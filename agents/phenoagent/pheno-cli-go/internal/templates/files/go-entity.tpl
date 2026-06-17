package domain

import (
	"context"
	"errors"
	"time"

	"github.com/google/uuid"
)

type Entity struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

func NewEntity(name, description string) *Entity {
	now := time.Now()
	return &Entity{
		ID:          uuid.New().String(),
		Name:        name,
		Description: description,
		CreatedAt:   now,
		UpdatedAt:   now,
	}
}

func (e *Entity) Update(name, description string) {
	e.Name = name
	e.Description = description
	e.UpdatedAt = time.Now()
}

type Repository interface {
	Create(ctx context.Context, entity *Entity) error
	GetByID(ctx context.Context, id string) (*Entity, error)
	Update(ctx context.Context, entity *Entity) error
	Delete(ctx context.Context, id string) error
	List(ctx context.Context) ([]*Entity, error)
}

var (
	ErrEntityNotFound = errors.New("entity not found")
	ErrInvalidInput   = errors.New("invalid input")
)

type InMemoryEntityRepository struct {
	entities map[string]*Entity
}

func NewInMemoryEntityRepository() *InMemoryEntityRepository {
	return &InMemoryEntityRepository{
		entities: make(map[string]*Entity),
	}
}

func (r *InMemoryEntityRepository) Create(ctx context.Context, entity *Entity) error {
	r.entities[entity.ID] = entity
	return nil
}

func (r *InMemoryEntityRepository) GetByID(ctx context.Context, id string) (*Entity, error) {
	entity, ok := r.entities[id]
	if !ok {
		return nil, ErrEntityNotFound
	}
	return entity, nil
}

func (r *InMemoryEntityRepository) Update(ctx context.Context, entity *Entity) error {
	r.entities[entity.ID] = entity
	return nil
}

func (r *InMemoryEntityRepository) Delete(ctx context.Context, id string) error {
	delete(r.entities, id)
	return nil
}

func (r *InMemoryEntityRepository) List(ctx context.Context) ([]*Entity, error) {
	result := make([]*Entity, 0, len(r.entities))
	for _, entity := range r.entities {
		result = append(result, entity)
	}
	return result, nil
}
