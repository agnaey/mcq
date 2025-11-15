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
    # In the MCQ model
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    mcqs = models.TextField()  # Store JSON data as a string

    def save(self, *args, **kwargs):
        # Convert the list of MCQs to a JSON string before saving
        self.mcqs = json.dumps(self.mcqs)
        super().save(*args, **kwargs)

    def get_mcqs(self):
        # Convert the JSON string back to a Python list
        return json.loads(self.mcqs)

    def __str__(self):
        return f"MCQ Batch created at {self.created_at}"