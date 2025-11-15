from django import forms
from django.contrib.auth.models import User

from .models import Profile

CHOICES_QA = [
    ('general', 'General'),
    ('t5-llm', 'Science'),  # lowercase to match view logic
]

CHOICES_Key = [
    ('rake', 'Rake'),
    ('spacy', 'Spacy'),
    ('distilbert', 'LLM DistilBERT'),  # lowercase to match view logic
]
CHOICES_Distractors = [
    ('s2v', 'Sense2Vec'),
    ('t5-llm', 'LLM T5'),
    ('llama', 'LLAMA'),
]

class InputForm(forms.Form):
    context = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter your context here...'}), 
        label="Context",
        required=False)
    pdf_file = forms.FileField(
        label="Upload PDF",
        help_text="Upload a PDF file for content extraction",
        required=False,  # Make it optional if the user can fill out the context manually
    )
    num_keywords = forms.IntegerField(
        label="Number of Keywords",
        min_value=1,
        initial=4,  # Default value, can be changed
        help_text="Select how many keywords to use for generating MCQs",
        widget=forms.NumberInput(attrs={'class': 'custom-number-input'})
    )
    option_1 = forms.ChoiceField(
        widget=forms.RadioSelect, 
        choices=CHOICES_QA, 
        label="Select an option for Question Generation",
        # help_text="For general tasks, select 'General'. For science-related tasks, select 'Science'"
    )
    option_2 = forms.ChoiceField(
        widget=forms.RadioSelect, 
        choices=CHOICES_Key, 
        label="Select an option for keyword extraction",
        # help_text="General -->'Rake', Science -->'LLM DistilBERT' and 'Spacy' for efficient keyword extraction"
    )
    option_3 = forms.ChoiceField(
        widget=forms.RadioSelect, 
        choices=CHOICES_Distractors, 
        label="Select an option for distractors generation",
        # help_text="General -->'Sense2Vec', science -->'LLM T5' and 'LLAMA' for efficient distractors generation"
    )

    def __init__(self, *args, **kwargs):
        super(InputForm, self).__init__(*args, **kwargs)
        self.fields['option_1'].initial = 'general'  # Match the key in CHOICES_Key
        self.fields['option_2'].initial = 'rake'   # Match the key in CHOICES_Distractors
        self.fields['option_3'].initial = 's2v'
    def clean_pdf_file(self):
        pdf_file = self.cleaned_data.get("pdf_file")
        if pdf_file and not pdf_file.name.endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are allowed.")
        return pdf_file
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username','email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']
    user_dropdown = forms.ModelChoiceField(
    queryset=User.objects.all(),
    empty_label="Select a user",
    widget=forms.Select(attrs={'class': 'form-control'})  # Add custom classes if needed
    )

    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Customize the choices for the dropdown (user_dropdown)
        self.fields['user_dropdown'].label_from_instance = lambda user: f"{user.username} ({user.email})"
