"""
NVMS format parser.
"""

import yaml


class NVMSParser:
    """
    Parse Byteport NVMS format.
    """

    def parse(self, nvms_file: str) -> dict:
        """
        Parse .nvms file.
        """
        with open(nvms_file) as f:
            return yaml.safe_load(f)

    def compile_to_vercel(self, config: dict) -> dict:
        """
        Compile to vercel.json.
        """
        return {
            "version": 2,
            "builds": [
                {"src": svc["path"], "use": "@vercel/node"}
                for svc in config.get("services", {}).values()
            ],
        }
