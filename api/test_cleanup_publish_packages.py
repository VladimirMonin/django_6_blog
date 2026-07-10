from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.utils import timezone

from api.models import ApiKey, PublishPackage
from blog.models import PostMedia


@pytest.mark.django_db
def test_cleanup_publish_packages_deletes_only_stale_owned_names(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    storage = PostMedia._meta.get_field("file").storage
    name = storage.save("posts/stale/packages/key/a001.png", ContentFile(b"data"))
    package = PublishPackage.objects.create(
        api_key=ApiKey.objects.create(name="Cleanup"),
        idempotency_key="stale-key-0001",
        payload_sha256="a" * 64,
        state=PublishPackage.State.PENDING,
        storage_names=[name],
    )
    PublishPackage.objects.filter(pk=package.pk).update(updated_at=timezone.now() - timedelta(hours=25))

    call_command("cleanup_publish_packages", older_than_hours=24)

    package.refresh_from_db()
    assert package.state == PublishPackage.State.FAILED
    assert package.storage_names == []
    assert not storage.exists(name)
