import json

from django.contrib.auth.models import User
from django.db import models
from PIL import Image
from django.db import models

class User(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    def __str__(self):
        return self.email



# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    image = models.ImageField(default='profile_pics/default.jpg',upload_to='profile_pics')

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self,*args,**kwargs):
        super().save(*args,**kwargs)

        img = Image.open(self.image.path)

        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
class MCQ(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    mcqs = models.TextField()  # Always store JSON string

    def save(self, *args, **kwargs):
        # Only encode if mcqs is NOT already a string
        if isinstance(self.mcqs, (list, dict)):
            self.mcqs = json.dumps(self.mcqs)

        super().save(*args, **kwargs)

    def get_mcqs(self):
        try:
            return json.loads(self.mcqs)
        except:
            # If it's already a Python list
            return self.mcqs

    def __str__(self):
        return f"MCQ Batch created at {self.created_at}"


class MCQHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    input_text = models.TextField()
    mcq_data = models.TextField() 
    created_at = models.DateTimeField(auto_now_add=True)

    def get_mcqs(self):
        try:
            return json.loads(self.mcq_data)
        except:
            return []
        

