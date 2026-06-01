using System;
using System.IO;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading.Tasks;

namespace Phenotype.Shim
{
    /// <summary>
    /// Skill manifest definition
    /// </summary>
    public class SkillManifest
    {
        public string Name { get; set; } = "";
        public string Version { get; set; } = "";
        public string? Description { get; set; }
        public string? Author { get; set; }
        public string Runtime { get; set; } = "wasm";
        public string? EntryPoint { get; set; }
        public List<SkillDependency> Dependencies { get; set; } = new();
        public List<SkillPermission> Permissions { get; set; } = new();
        public string Priority { get; set; } = "normal";
        public Dictionary<string, string> Metadata { get; set; } = new();
    }

    public class SkillDependency
    {
        public string Name { get; set; } = "";
        public string VersionConstraint { get; set; } = "";
        public bool Optional { get; set; } = false;
    }

    public class SkillPermission
    {
        public string Name { get; set; } = "";
        public string? Description { get; set; }
    }

    /// <summary>
    /// Phenotype client - auto-spawns daemon if needed
    /// Thin wrapper (~100 lines) that communicates with phenotype-daemon
    /// via Unix sockets using msgpack-rpc. Much faster than stdio MCP.
    /// </summary>
    public class PhenotypeClient : IDisposable
    {
        private readonly string _socketPath;
        private System.Diagnostics.Process? _daemonProcess;

        public PhenotypeClient(string? socketPath = null)
        {
            _socketPath = socketPath ?? "/tmp/phenotype.sock";
        }

        /// <summary>
        /// Ensure daemon is running
        /// </summary>
        private async Task EnsureDaemonAsync()
        {
            if (File.Exists(_socketPath))
            {
                try
                {
                    await PingAsync();
                    return;
                }
                catch
                {
                    // Stale socket, remove it
                    File.Delete(_socketPath);
                }
            }

            // Spawn daemon
            var daemonPath = FindDaemon();
            _daemonProcess = new System.Diagnostics.Process
            {
                StartInfo = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = daemonPath,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                }
            };
            _daemonProcess.Start();

            // Wait for socket
            for (int i = 0; i < 50; i++)
            {
                await Task.Delay(100);
                if (File.Exists(_socketPath))
                    return;
            }

            throw new InvalidOperationException("Daemon failed to start");
        }

        private string FindDaemon()
        {
            var candidates = new[]
            {
                Path.Combine(AppContext.BaseDirectory, "phenotype-daemon"),
                Path.Combine(AppContext.BaseDirectory, "..", "..", "phenotype-daemon"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".cargo", "bin", "phenotype-daemon"),
                "phenotype-daemon"
            };

            foreach (var candidate in candidates)
            {
                if (File.Exists(candidate))
                    return candidate;
            }

            return "phenotype-daemon"; // Hope it's in PATH
        }

        /// <summary>
        /// Make RPC call using msgpack
        /// </summary>
        private async Task<JsonElement> RpcAsync(string method, object parameters)
        {
            await EnsureDaemonAsync();

            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                // Windows: use TCP instead of Unix socket
                return await RpcTcpAsync(method, parameters);
            }

            using var socket = new Socket(AddressFamily.Unix, SocketType.Stream, 0);
            socket.Connect(new UnixDomainSocketEndPoint(_socketPath));

            // Serialize request
            var request = new { method, @params = parameters };
            var requestJson = JsonSerializer.Serialize(request);
            var requestBytes = System.Text.Encoding.UTF8.GetBytes(requestJson);

            // Send length-prefixed message
            var lengthBytes = BitConverter.GetBytes(requestBytes.Length);
            if (BitConverter.IsLittleEndian)
                Array.Reverse(lengthBytes);

            await socket.SendAsync(lengthBytes, SocketFlags.None);
            await socket.SendAsync(requestBytes, SocketFlags.None);

            // Receive response
            var lengthBuffer = new byte[4];
            await socket.ReceiveAsync(lengthBuffer, SocketFlags.None);
            if (BitConverter.IsLittleEndian)
                Array.Reverse(lengthBuffer);

            var responseLength = BitConverter.ToInt32(lengthBuffer, 0);
            var responseBuffer = new byte[responseLength];
            await socket.ReceiveAsync(responseBuffer, SocketFlags.None);

            var responseJson = System.Text.Encoding.UTF8.GetString(responseBuffer);
            var response = JsonSerializer.Deserialize<JsonElement>(responseJson);

            if (response.GetProperty("result").GetString() == "error")
            {
                throw new InvalidOperationException(
                    response.GetProperty("message").GetString() ?? "RPC error");
            }

            return response.GetProperty("data");
        }

        private async Task<JsonElement> RpcTcpAsync(string method, object parameters)
        {
            using var client = new TcpClient("127.0.0.1", 9753);
            using var stream = client.GetStream();

            // Same msgpack/JSON protocol
            var request = new { method, @params = parameters };
            var requestJson = JsonSerializer.Serialize(request);
            var requestBytes = System.Text.Encoding.UTF8.GetBytes(requestJson);

            var lengthBytes = BitConverter.GetBytes(requestBytes.Length);
            if (BitConverter.IsLittleEndian)
                Array.Reverse(lengthBytes);

            await stream.WriteAsync(lengthBytes);
            await stream.WriteAsync(requestBytes);

            var lengthBuffer = new byte[4];
            await stream.ReadAsync(lengthBuffer);
            if (BitConverter.IsLittleEndian)
                Array.Reverse(lengthBuffer);

            var responseLength = BitConverter.ToInt32(lengthBuffer, 0);
            var responseBuffer = new byte[responseLength];
            await stream.ReadAsync(responseBuffer);

            var responseJson = System.Text.Encoding.UTF8.GetString(responseBuffer);
            var response = JsonSerializer.Deserialize<JsonElement>(responseJson);

            if (response.GetProperty("result").GetString() == "error")
            {
                throw new InvalidOperationException(
                    response.GetProperty("message").GetString() ?? "RPC error");
            }

            return response.GetProperty("data");
        }

        // === Public API ===

        public async Task<string> PingAsync()
        {
            var result = await RpcAsync("ping", new { });
            return result.GetString()!;
        }

        public async Task<string> RegisterSkillAsync(SkillManifest manifest)
        {
            var result = await RpcAsync("skill.register", new { manifest });
            return result.GetProperty("id").GetString()!;
        }

        public async Task<SkillManifest?> GetSkillAsync(string skillId)
        {
            try
            {
                var result = await RpcAsync("skill.get", new { id = skillId });
                return JsonSerializer.Deserialize<SkillManifest>(result.GetRawText());
            }
            catch
            {
                return null;
            }
        }

        public async Task<List<string>> ListSkillsAsync()
        {
            var result = await RpcAsync("skill.list", new { });
            return result.Deserialize<List<string>>()!;
        }

        public async Task UnregisterSkillAsync(string skillId)
        {
            await RpcAsync("skill.unregister", new { id = skillId });
        }

        public async Task<bool> SkillExistsAsync(string skillId)
        {
            var result = await RpcAsync("skill.exists", new { id = skillId });
            return result.GetBoolean();
        }

        public async Task<List<string>> ResolveDependenciesAsync(List<string> skillIds)
        {
            var result = await RpcAsync("resolve", new { skill_ids = skillIds });
            return result.GetProperty("resolved").Deserialize<List<string>>()!;
        }

        public async Task<bool> CheckCircularAsync(List<string> skillIds)
        {
            try
            {
                var result = await RpcAsync("check_circular", new { skill_ids = skillIds });
                return result.GetProperty("circular").GetBoolean();
            }
            catch
            {
                return true; // Error indicates circular
            }
        }

        public async Task<JsonElement> VersionAsync()
        {
            return await RpcAsync("version", new { });
        }

        public void Dispose()
        {
            _daemonProcess?.Kill();
            _daemonProcess?.Dispose();
        }
    }
}
