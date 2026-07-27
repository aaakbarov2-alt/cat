from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("exams", "0007_question_explanation_question_passage_reference")]

    operations = [
        migrations.AddField(
            model_name="examset",
            name="delivery_mode",
            field=models.CharField(
                choices=[("native", "Adaptive platform test"), ("exact_html", "Exact uploaded HTML")],
                default="native",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="examset",
            name="source_html",
            field=models.TextField(blank=True),
        ),
    ]
