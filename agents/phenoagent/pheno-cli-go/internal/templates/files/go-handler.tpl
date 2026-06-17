package http

import (
	"encoding/json"
	"net/http"

	"{{.RepoName}}/internal/application"
)

type Handler struct {
	service *application.EntityService
}

func NewHandler(service *application.EntityService) *Handler {
	return &Handler{service: service}
}

func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/health", h.handleHealth)
	mux.HandleFunc("/entities", h.handleEntities)
	mux.HandleFunc("/entities/", h.handleEntity)
}

func (h *Handler) handleHealth(w http.ResponseWriter, r *http.Request) {
	respondJSON(w, http.StatusOK, map[string]string{"status": "healthy"})
}

func (h *Handler) handleEntities(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.listEntities(w, r)
	case http.MethodPost:
		h.createEntity(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (h *Handler) handleEntity(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Path[len("/entities/"):]
	if id == "" {
		http.Error(w, "Entity ID required", http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		h.getEntity(w, r, id)
	case http.MethodPut:
		h.updateEntity(w, r, id)
	case http.MethodDelete:
		h.deleteEntity(w, r, id)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (h *Handler) createEntity(w http.ResponseWriter, r *http.Request) {
	var input application.CreateEntityInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	entity, err := h.service.Create(r.Context(), input)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	respondJSON(w, http.StatusCreated, entity)
}

func (h *Handler) getEntity(w http.ResponseWriter, r *http.Request, id string) {
	entity, err := h.service.GetEntity(r.Context(), id)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	respondJSON(w, http.StatusOK, entity)
}

func (h *Handler) updateEntity(w http.ResponseWriter, r *http.Request, id string) {
	var input application.UpdateEntityInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}
	input.ID = id

	entity, err := h.service.UpdateEntity(r.Context(), input)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	respondJSON(w, http.StatusOK, entity)
}

func (h *Handler) deleteEntity(w http.ResponseWriter, r *http.Request, id string) {
	if err := h.service.DeleteEntity(r.Context(), id); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *Handler) listEntities(w http.ResponseWriter, r *http.Request) {
	entities, err := h.service.ListEntities(r.Context())
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	respondJSON(w, http.StatusOK, entities)
}

func respondJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}
