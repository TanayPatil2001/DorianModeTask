# from django import forms
# from .models import ProcessedData
# class UploadFileForm(forms.ModelForm):
#     class Meta:
#         model = ProcessedData
#         fields = ['file']

from django import forms
from .models import ProcessedData

class UploadFileForm(forms.Form):
    file1 = forms.FileField(label='First File')
    file2 = forms.FileField(label='Second File')

