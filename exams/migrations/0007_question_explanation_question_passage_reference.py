from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("exams", "0008_examset_category")]

    operations = [
        migrations.AddField(
            model_name="question",
            name="explanation",
            field=models.TextField(blank=True, help_text="Shown to students in review mode after they submit the test."),
        ),
        migrations.AddField(
            model_name="question",
            name="passage_reference",
            field=models.TextField(blank=True, help_text="Optional exact sentence or short excerpt from the reading passage that supports this answer."),
        ),
    ]
