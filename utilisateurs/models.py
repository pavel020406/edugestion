from django.contrib.auth.models import AbstractUser
from django.db import models
 
 
class Utilisateur(AbstractUser):
   
 
    ROLE_CHOICES = [
        ('admin',      'Administrateur'),
        ('enseignant', 'Enseignant'),
        ('eleve',      'Élève'),
        ('secretaire',  'Secretaire'),
         ('parent',  'Parent'),
    ]
 
    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
 
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='eleve')
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES, blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)
 
   
    photo_profil = models.ImageField(
        upload_to='photos_profil/',
        null=True,
        blank=True,
        verbose_name="Photo de profil",
    )
 
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
 
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
 
 

 
