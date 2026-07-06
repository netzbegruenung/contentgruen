"""
Test module for QdrantRepositoryFactory using the new dependency injection architecture.

This module demonstrates clean testing patterns without complex mocking.
"""

import pytest
from unittest.mock import MagicMock

from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from repositories.implementations.qdrant.statement_repository import (
    StatementRepository,
)
from repositories.implementations.qdrant.commentary_repository import (
    CommentaryRepository,
)
from repositories.implementations.qdrant.reference_repository import (
    ReferenceRepository,
)
from repositories.implementations.qdrant.generic_text_repository import (
    GenericTextRepository,
)
from repositories.aggregated.content_repository import ContentRepository
from repositories.interfaces.repository_factory import IRepositoryFactory


@pytest.mark.unit
class TestQdrantRepositoryFactory:
    """Test QdrantRepositoryFactory implementation."""

    @pytest.fixture
    def factory(self, test_embeddings_manager):
        """Create repository factory instance with test embeddings manager."""
        return QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)

    @pytest.fixture
    def factory_without_manager(self):
        """Create repository factory without embeddings manager."""
        return QdrantRepositoryFactory()

    def test_factory_implements_interface(self, factory):
        """Test that factory implements the repository factory interface."""
        assert isinstance(factory, IRepositoryFactory)

    def test_factory_initialization_with_embeddings_manager(
        self, factory, test_embeddings_manager
    ):
        """Test factory initialization with embeddings manager."""
        assert factory._embeddings_manager == test_embeddings_manager

    def test_factory_initialization_without_embeddings_manager(
        self, factory_without_manager
    ):
        """Test factory initialization without embeddings manager."""
        assert factory_without_manager._embeddings_manager is None

    def test_create_statement_repository(
        self, factory, test_settings, test_embeddings_manager
    ):
        """Test creating statement repository."""
        # Act
        result = factory.create_statement_repository(test_settings)

        # Assert
        assert isinstance(result, StatementRepository)
        assert result._shared_manager == test_embeddings_manager
        assert result.repository_name == "statement_index"
        assert result.content_type == "statement"

    def test_create_commentary_repository(
        self, factory, test_settings, test_embeddings_manager
    ):
        """Test creating commentary repository."""
        # Act
        result = factory.create_commentary_repository(test_settings)

        # Assert
        assert isinstance(result, CommentaryRepository)
        assert result._shared_manager == test_embeddings_manager
        assert result.repository_name == "commentary_index"
        assert result.content_type == "commentary"

    def test_create_reference_repository(
        self, factory, test_settings, test_embeddings_manager
    ):
        """Test creating reference repository."""
        # Act
        result = factory.create_reference_repository(test_settings)

        # Assert
        assert isinstance(result, ReferenceRepository)
        assert result._shared_manager == test_embeddings_manager
        assert result.repository_name == "reference_index"
        assert result.content_type == "reference"

    def test_create_generic_text_repository(
        self, factory, test_settings, test_embeddings_manager
    ):
        """Test creating generic text repository."""
        # Act
        result = factory.create_generic_text_repository(test_settings)

        # Assert
        assert isinstance(result, GenericTextRepository)
        assert result._shared_manager == test_embeddings_manager
        assert result.repository_name == "generic_text_index"
        assert result.content_type == "generic_text"

    def test_create_content_repository(
        self, factory, test_settings, test_embeddings_manager
    ):
        """Test creating content repository."""
        # Act
        result = factory.create_content_repository(test_settings)

        # Assert
        assert isinstance(result, ContentRepository)
        assert result._shared_manager == test_embeddings_manager
        assert result.repository_name == "content_index"
        assert result.content_type is None  # Aggregated repository

    def test_create_all_repositories(self, factory, test_settings):
        """Test creating all repositories without mocking to verify actual instantiation."""
        # Act - Create all repository types
        statement_repo = factory.create_statement_repository(test_settings)
        commentary_repo = factory.create_commentary_repository(test_settings)
        reference_repo = factory.create_reference_repository(test_settings)
        generic_text_repo = factory.create_generic_text_repository(test_settings)
        content_repo = factory.create_content_repository(test_settings)

        # Assert - Verify correct types are returned
        assert isinstance(statement_repo, StatementRepository)
        assert isinstance(commentary_repo, CommentaryRepository)
        assert isinstance(reference_repo, ReferenceRepository)
        assert isinstance(generic_text_repo, GenericTextRepository)
        assert isinstance(content_repo, ContentRepository)

        # Verify all repositories are properly initialized
        assert statement_repo.repository_name == "statement_index"
        assert commentary_repo.repository_name == "commentary_index"
        assert reference_repo.repository_name == "reference_index"
        assert generic_text_repo.repository_name == "generic_text_index"
        assert content_repo.repository_name == "content_index"

    def test_factory_creates_new_instances_on_each_call(self, factory, test_settings):
        """Test that factory creates new instances on each call (no caching)."""
        # Act
        result1 = factory.create_statement_repository(test_settings)
        result2 = factory.create_statement_repository(test_settings)

        # Assert - Each call should create a new instance
        assert result1 is not result2
        assert id(result1) != id(result2)
        # But they should have the same configuration
        assert result1.repository_name == result2.repository_name == "statement_index"
        assert result1.content_type == result2.content_type == "statement"

    def test_factory_passes_embeddings_manager_to_all_repositories(
        self, factory, test_settings, test_embeddings_manager
    ):
        """Test that factory passes embeddings manager to all created repositories."""
        # Create all repositories
        repositories = [
            factory.create_statement_repository(test_settings),
            factory.create_commentary_repository(test_settings),
            factory.create_reference_repository(test_settings),
            factory.create_generic_text_repository(test_settings),
            factory.create_content_repository(test_settings),
        ]

        # Verify all repositories received the embeddings manager
        for repo in repositories:
            assert repo._shared_manager == test_embeddings_manager


@pytest.mark.unit
class TestQdrantRepositoryFactoryWithoutEmbeddingsManager:
    """Test QdrantRepositoryFactory without injected embeddings manager."""

    @pytest.fixture
    def factory(self):
        """Create repository factory without embeddings manager."""
        return QdrantRepositoryFactory()

    def test_create_repositories_uses_default_singleton(self, factory, test_settings):
        """Test that repositories use default singleton when no manager is provided."""
        # When no embeddings manager is provided, repositories will attempt
        # to use the default singleton. In tests, this will fail if the
        # singleton hasn't been initialized.

        # This should raise an error since no embeddings manager was provided
        # and the singleton hasn't been initialized
        with pytest.raises(
            RuntimeError, match="QdrantEmbeddingsManager not initialized"
        ):
            factory.create_statement_repository(test_settings)


@pytest.mark.unit
class TestRepositoryFactoryIntegration:
    """Test integration scenarios with the repository factory."""

    @pytest.fixture
    def factory(self, test_embeddings_manager):
        """Create repository factory instance with test embeddings manager."""
        return QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)

    def test_all_repositories_use_same_embeddings_manager(
        self, factory, test_settings, test_embeddings_manager
    ):
        """Test that all repositories created by factory use the same embeddings manager."""
        # Create multiple repositories
        statement_repo = factory.create_statement_repository(test_settings)
        commentary_repo = factory.create_commentary_repository(test_settings)
        reference_repo = factory.create_reference_repository(test_settings)
        generic_text_repo = factory.create_generic_text_repository(test_settings)
        content_repo = factory.create_content_repository(test_settings)

        # Verify all repositories share the same embeddings manager
        repositories = [
            statement_repo,
            commentary_repo,
            reference_repo,
            generic_text_repo,
            content_repo,
        ]

        for repo in repositories:
            assert repo._shared_manager == test_embeddings_manager

    def test_factory_creates_repositories_with_correct_content_types(
        self, factory, test_settings
    ):
        """Test that factory creates repositories with correct content type filters."""
        # Create repositories
        statement_repo = factory.create_statement_repository(test_settings)
        commentary_repo = factory.create_commentary_repository(test_settings)
        reference_repo = factory.create_reference_repository(test_settings)
        generic_text_repo = factory.create_generic_text_repository(test_settings)
        content_repo = factory.create_content_repository(test_settings)

        # Verify content type filters
        assert statement_repo.content_type == "statement"
        assert commentary_repo.content_type == "commentary"
        assert reference_repo.content_type == "reference"
        assert generic_text_repo.content_type == "generic_text"
        assert content_repo.content_type is None  # Aggregated repository has no filter

    def test_multiple_factories_create_independent_repositories(
        self, test_settings, test_embeddings_manager
    ):
        """Test that multiple factory instances create independent repositories."""
        # Create two factory instances with the same embeddings manager
        factory1 = QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)
        factory2 = QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)

        # Create repositories from both factories
        repo1 = factory1.create_statement_repository(test_settings)
        repo2 = factory2.create_statement_repository(test_settings)

        # Verify they are different instances
        assert repo1 is not repo2
        assert id(repo1) != id(repo2)

        # But they should have the same embeddings manager
        assert repo1._shared_manager == repo2._shared_manager == test_embeddings_manager
        assert repo1.repository_name == repo2.repository_name == "statement_index"

    def test_factory_repository_initialization_flow(self, factory, test_settings):
        """Test the complete initialization flow when creating repositories."""
        # Act
        statement_repo = factory.create_statement_repository(test_settings)

        # Assert - Verify initialization flow
        assert statement_repo is not None

        # The repository should be ready to use
        assert hasattr(statement_repo, "_shared_manager")
        assert hasattr(statement_repo, "content_type")
        assert hasattr(statement_repo, "repository_name")
        assert statement_repo.content_type == "statement"
        assert statement_repo.repository_name == "statement_index"

    def test_factory_performance_with_multiple_repository_creation(
        self, factory, test_settings
    ):
        """Test factory performance when creating many repositories."""
        # Create many repositories to test performance
        repositories = []

        for _ in range(10):  # Create 10 of each type
            repositories.extend(
                [
                    factory.create_statement_repository(test_settings),
                    factory.create_commentary_repository(test_settings),
                    factory.create_reference_repository(test_settings),
                    factory.create_generic_text_repository(test_settings),
                    factory.create_content_repository(test_settings),
                ]
            )

        # Verify all repositories were created successfully
        assert len(repositories) == 50

        # Verify all are distinct instances
        repository_ids = [id(repo) for repo in repositories]
        assert len(set(repository_ids)) == 50  # All unique instances

        # Verify they all have proper initialization
        for repo in repositories:
            assert hasattr(repo, "_shared_manager")
            assert hasattr(repo, "repository_name")
            assert hasattr(repo, "content_type")

    def test_factory_interface_compliance(self, factory):
        """Test that factory implements all required interface methods."""
        # Verify all required methods exist
        required_methods = [
            "create_statement_repository",
            "create_commentary_repository",
            "create_reference_repository",
            "create_generic_text_repository",
            "create_content_repository",
        ]

        for method_name in required_methods:
            assert hasattr(factory, method_name)
            assert callable(getattr(factory, method_name))

    def test_factories_with_different_embeddings_managers(self, test_settings):
        """Test factories with different embeddings managers create isolated repositories."""
        from tests.fixtures.test_embeddings_manager import TestEmbeddingsManager

        # Create two different embeddings managers
        embeddings1 = TestEmbeddingsManager()
        embeddings2 = TestEmbeddingsManager()

        # Create factories with different managers
        factory1 = QdrantRepositoryFactory(embeddings_manager=embeddings1)
        factory2 = QdrantRepositoryFactory(embeddings_manager=embeddings2)

        # Create repositories
        repo1 = factory1.create_statement_repository(test_settings)
        repo2 = factory2.create_statement_repository(test_settings)

        # Verify they use different embeddings managers
        assert repo1._shared_manager == embeddings1
        assert repo2._shared_manager == embeddings2
        assert repo1._shared_manager != repo2._shared_manager
