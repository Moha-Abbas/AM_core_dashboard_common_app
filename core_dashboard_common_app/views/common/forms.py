"""
Common Forms
"""
from django import forms

from core_main_app.components.user import api as user_api


class ActionForm(forms.Form):
    """
    Form to select the action in the user dashboard.
    """

    actions = forms.ChoiceField(label="", required=True, choices=[])

    def __init__(self, list_actions):
        super().__init__()
        self.fields["actions"].choices = list_actions


class UserForm(forms.Form):
    """
    Form to select a user.
    """

    users = forms.ChoiceField(label="", required=True)
    user_options = []

    def __init__(self, current_user, current_owner_id=None):
        self.user_options = []

        # We retrieve all users
        sort_users = user_api.get_active_users()
        # We sort by username, case insensitive
        sort_users = sorted(sort_users, key=lambda s: s.username.lower())

        # We add them
        current_owner_in_list = False
        for user in sort_users:
            if user.id != current_user.id or current_user.is_superuser:
                self.user_options.append((user.id, user.username))
                if current_owner_id and str(user.id) == str(current_owner_id):
                    current_owner_in_list = True

        # Fall back to a blank choice only if we don't have a real owner to
        # preselect - otherwise the dropdown always opens on a real user.
        if not current_owner_in_list:
            self.user_options.insert(0, ("", "-----------"))

        super().__init__()
        self.fields["users"].choices = []
        self.fields["users"].choices = self.user_options
        if current_owner_in_list:
            self.fields["users"].initial = str(current_owner_id)
