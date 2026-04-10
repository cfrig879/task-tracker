from django import forms

class TaskImportForm(forms.Form):
    file = forms.FileField(label="CSV file")