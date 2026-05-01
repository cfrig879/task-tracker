from django import forms
from django.core.exceptions import ValidationError


class TaskImportForm(forms.Form):
    file = forms.FileField(
        label="Cadence Excel template (.xlsx)",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
        help_text="Upload the Cadence task import template (.xlsx).",
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        name = (f.name or "").lower()
        if not name.endswith(".xlsx"):
            raise ValidationError("Please upload the Cadence Excel template (.xlsx).")
        return f