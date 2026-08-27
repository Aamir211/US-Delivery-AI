from app.config import get_settings
from app.services.dataset import DatasetRepository


def test_dataset_repository_is_read_only_and_validates_inputs() -> None:
    settings = get_settings()
    repository = DatasetRepository(settings.data_directory, settings.knowledge_base_directory)

    assert len(repository.tickets) == 500
    assert len(repository.accounts) == 50
    assert len(repository.knowledge_base_paths) == 9
    assert len(repository.tickets_by_account_id) == 484
