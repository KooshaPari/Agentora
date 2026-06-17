package application

import (
	"context"
	"fmt"

	"{{.RepoName}}/internal/domain"
)

type EntityService struct {
	repo domain.Repository
}

func NewEntityService(repo domain.Repository) *EntityService {
	return &EntityService{repo: repo}
}

type CreateEntityInput struct {
	Name        string
	Description string
}

func (s *EntityService) Create(ctx context.Context, input CreateEntityInput) (*domain.Entity, error) {
	if input.Name == "" {
		return nil, fmt.Errorf("%w: name is required", domain.ErrInvalidInput)
	}

	entity := domain.NewEntity(input.Name, input.Description)
	if err := s.repo.Create(ctx, entity); err != nil {
		return nil, fmt.Errorf("failed to create entity: %w", err)
	}

	return entity, nil
}

func (s *EntityService) GetEntity(ctx context.Context, id string) (*domain.Entity, error) {
	entity, err := s.repo.GetByID(ctx, id)
	if err != nil {
		return nil, fmt.Errorf("failed to get entity: %w", err)
	}
	return entity, nil
}

type UpdateEntityInput struct {
	ID          string
	Name        string
	Description string
}

func (s *EntityService) UpdateEntity(ctx context.Context, input UpdateEntityInput) (*domain.Entity, error) {
	entity, err := s.repo.GetByID(ctx, input.ID)
	if err != nil {
		return nil, fmt.Errorf("failed to get entity for update: %w", err)
	}

	entity.Update(input.Name, input.Description)
	if err := s.repo.Update(ctx, entity); err != nil {
		return nil, fmt.Errorf("failed to update entity: %w", err)
	}

	return entity, nil
}

func (s *EntityService) DeleteEntity(ctx context.Context, id string) error {
	if err := s.repo.Delete(ctx, id); err != nil {
		return fmt.Errorf("failed to delete entity: %w", err)
	}
	return nil
}

func (s *EntityService) ListEntities(ctx context.Context) ([]*domain.Entity, error) {
	entities, err := s.repo.List(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to list entities: %w", err)
	}
	return entities, nil
}
