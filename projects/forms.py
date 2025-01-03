from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, get_user_model
from .models import Project, Task, User, Profile, Team, TeamMember, File
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django import forms


# Project Form
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'team', 'status', 'start_date', 'end_date', 'priority']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'team': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),  # Changed from due_date to end_date
            'priority': forms.Select(attrs={'class': 'form-control'})
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')  # Changed from due_date to end_date

        if start_date and end_date and start_date > end_date:
            raise ValidationError({'end_date': 'End date must be after start date'})  # Changed error message to use end_date

        return cleaned_data

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'description', 'avatar']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter team name',
                'required': True,
                'minlength': 3,
                'maxlength': 100
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe the team\'s purpose and goals',
                'rows': 4,
                'maxlength': 500
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Check file size (2MB limit)
            if avatar.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image file too large ( > 2MB )")
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            ext = avatar.name.lower().split('.')[-1]
            if f'.{ext}' not in valid_extensions:
                raise forms.ValidationError("Only JPG, JPEG, PNG and GIF files are allowed")
            
            # Validate image using Pillow
            try:
                from PIL import Image
                img = Image.open(avatar)
                img.verify()  # Verify it's a valid image
                
                # Check image format
                if img.format.lower() not in ['jpeg', 'png', 'gif']:
                    raise forms.ValidationError("Invalid image format")
                    
            except Exception as e:
                raise forms.ValidationError("Invalid image file")
                
        return avatar


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'title',
            'description',
            'project',  # Important: Include project field
            'start_date',
            'due_date',
            'priority',
            'assigned_to',
            'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter task title',
                'minlength': '3',
                'maxlength': '200'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the task details and requirements',
                'maxlength': '500'
            }),
            'project': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            })
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set choices for priority and status
        self.fields['priority'].choices = Task.PRIORITY_CHOICES
        self.fields['status'].choices = Task.STATUS_CHOICES

        # If project is provided, set it and filter assignees
        if project:
            self.fields['project'].initial = project
            self.fields['project'].widget = forms.HiddenInput()
            # Only show team members as assignee options
            self.fields['assigned_to'].queryset = User.objects.filter(
                teammember__team=project.team,
                is_active=True
            ).distinct()
        else:
            # If no project, show all projects user has access to
            self.fields['project'].queryset = Project.objects.all()
            self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        due_date = cleaned_data.get('due_date')
        project = cleaned_data.get('project')
        assigned_to = cleaned_data.get('assigned_to')

        # Validate dates
        if start_date and due_date and start_date > due_date:
            raise forms.ValidationError({
                'due_date': 'Due date must be after start date'
            })

        # Validate project membership for assigned user
        if project and assigned_to:
            if not project.team.members.filter(user=assigned_to).exists():
                raise forms.ValidationError({
                    'assigned_to': 'Selected user is not a member of the project team'
                })

        return cleaned_data

# Custom User Creation Form (for registration)
class CustomUserCreationForm(UserCreationForm):
    is_project_manager = forms.BooleanField(
        required=False,  # Changed to False since we set it in save()
        initial=True,
        widget=forms.HiddenInput()
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'autocomplete': 'email'
        })
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'minlength': '8',
            'autocomplete': 'new-password'
        })
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'minlength': '8',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'is_project_manager')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username',
                'autocomplete': 'username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_project_manager'].initial = True

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError("Username is required.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username.lower()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("Email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email.lower()

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if not password1 or not password2:
            raise ValidationError("Both password fields are required.")
        if password1 != password2:
            raise ValidationError("Passwords don't match.")
        if len(password1) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('username') or not cleaned_data.get('email'):
            raise ValidationError("Both username and email are required.")
        cleaned_data['is_project_manager'] = True
        return cleaned_data

    def save(self, commit=True):
        try:
            with transaction.atomic():
                user = super().save(commit=False)
                user.email = self.cleaned_data['email'].lower()
                user.username = self.cleaned_data['username'].lower()
                user.is_project_manager = True
                user.backend = 'django.contrib.auth.backends.ModelBackend'  # Add this line
                user.save()

                # Create profile if it doesn't exist
                Profile.objects.get_or_create(user=user)
                
                # Send welcome notification
                if hasattr(user, 'notify'):
                    user.notify(
                        "Account created successfully as Project Manager. You can now create and manage projects.",
                        notification_type='success',
                        action_type='registration'
                    )
                
                return user

        except Exception as e:
            raise ValidationError(f"Failed to create account: {str(e)}")

class CustomTeamMemberCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'autocomplete': 'email'
        })
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'minlength': '8',
            'autocomplete': 'new-password'
        })
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'minlength': '8',
            'autocomplete': 'new-password'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username',
                'autocomplete': 'username'
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError("Username is required.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        return username.lower()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("Email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email address is already registered.")
        return email.lower()

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if not password1 or not password2:
            raise ValidationError("Both password fields are required.")
        if password1 != password2:
            raise ValidationError("Passwords don't match.")
        if len(password1) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('username') or not cleaned_data.get('email'):
            raise ValidationError("Both username and email are required.")
        return cleaned_data

    def save(self, commit=True, team=None, created_by=None):
        if not team:
            raise ValidationError("Team is required to create a team member.")
        if not created_by:
            raise ValidationError("Creator information is required.")

        try:
            with transaction.atomic():
                # Create user with basic permissions
                user = super().save(commit=False)
                user.email = self.cleaned_data['email'].lower()
                user.username = self.cleaned_data['username'].lower()
                user.is_staff = False
                user.is_project_manager = False
                user.set_password(self.cleaned_data['password1'])
                user.save()

                # Create profile
                Profile.objects.get_or_create(user=user)

                # Create team membership as regular member
                member = TeamMember.objects.create(
                    team=team,
                    user=user,
                    role='member',  # Always create as basic member
                    created_by=created_by
                )

                # Send welcome notification
                if hasattr(user, 'notify'):
                    user.notify(
                        f"Welcome to {team.name}! Your account has been created successfully.",
                        notification_type='success',
                        action_type='team_joined',
                        related_object=team
                    )

                    # Notify team owner if someone else added the member
                    if team.owner != created_by:
                        team.owner.notify(
                            f"New member {user.username} added to {team.name} by {created_by.username}",
                            notification_type='info',
                            action_type='team_member_added',
                            related_object=team
                        )

                return member

        except IntegrityError:
            raise ValidationError("Failed to create team member: Database integrity error")
        except Exception as e:
            raise ValidationError(f"Failed to create team member: {str(e)}")

User = get_user_model()

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True,
            'id': 'id_username'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'id_password'
        })
    )

    remember = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'remember'
        })
    )

    error_messages = {
        'invalid_login': "Please enter a correct username/email and password.",
        'inactive': "This account is inactive.",
        'invalid_email': "No account found with this email address."
    }

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            # Check if input is email
            if '@' in username:
                try:
                    # Try to get user by email
                    user = User.objects.get(email__iexact=username)
                    self.cleaned_data['username'] = user.username
                except User.DoesNotExist:
                    raise ValidationError(
                        self.error_messages['invalid_email'],
                        code='invalid_login'
                    )
            
            # Authenticate with username/email and password
            user = self._authenticate_username_password(
                self.cleaned_data['username'], 
                password
            )
            
            if user:
                if not user.is_active:
                    raise ValidationError(
                        self.error_messages['inactive'],
                        code='inactive'
                    )
            else:
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login'
                )

            self.user_cache = user
        return self.cleaned_data

    def _authenticate_username_password(self, username, password):
        """Helper method to authenticate with username and password"""
        from django.contrib.auth import authenticate
        return authenticate(
            self.request,
            username=username,
            password=password
        )

    def get_user(self):
        return self.user_cache if hasattr(self, 'user_cache') else None

# Profile Form (to allow name and profile updates)
class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Profile
        fields = ['bio', 'profile_picture', 'date_of_birth', 'phone_number']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance').user if kwargs.get('instance') else None  # Ensure 'instance' exists
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name

    def save(self, commit=True):
        try:
            with transaction.atomic():
                profile = super().save(commit=False)
                # Save the user's first name and last name
                user = profile.user
                user.first_name = self.cleaned_data['first_name']
                user.last_name = self.cleaned_data['last_name']
                user.save()  # Save the user with updated names
                if commit:
                    profile.save()
                return profile
        except Exception as e:
            logger.error(f"Profile save error: {str(e)}")
            raise ValidationError("Failed to save profile changes")

# Team Member Form (for managing team members)
class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ['team', 'user']
        widgets = {
            'team': forms.Select(attrs={'class': 'form-control'}),
            'user': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        team = cleaned_data.get('team')
        user = cleaned_data.get('user')
        if TeamMember.objects.filter(team=team, user=user).exists():
            raise ValidationError("This user is already a member of the team.")
        return cleaned_data

# File Form (for file sharing)
class FileForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['task', 'file_name', 'file']
        widgets = {
            'task': forms.Select(attrs={'class': 'form-select'}),
            'file_name': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }

class ReportForm(forms.Form):
    """Form for generating reports"""
    REPORT_TYPES = (
        ('tasks', 'Tasks Report'),
        ('projects', 'Projects Report'),
        ('team', 'Team Performance Report'),
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Start date for report period"
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="End date for report period"
    )
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        help_text="Type of report to generate"
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date must be after start date")
        
        return cleaned_data

class ProjectSearchForm(forms.Form):
    """Form for searching projects"""
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search projects...'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All')] + Project.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class TeamSearchForm(forms.Form):
    """Form for searching teams"""
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search teams...'
        })
    )        