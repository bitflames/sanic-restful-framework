from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('models', '0001_initial')]

    initial = True

    operations = [
        ops.CreateModel(
            name='SecretNote',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('owner', fields.ForeignKeyField('models.User', source_field='owner_id', db_constraint=True, to_field='id', related_name='secret_notes', on_delete=OnDelete.CASCADE)),
                ('title', fields.CharField(unique=True, max_length=128)),
                ('body', fields.TextField(null=True, unique=False)),
            ],
            options={'table': 'app_server_secret_note', 'app': 'test_models', 'pk_attr': 'id', 'table_description': 'Per-user note with a globally unique title (for 409 / IDOR scenarios).'},
            bases=['Model'],
        ),
    ]
