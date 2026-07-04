from django.core.management.base import BaseCommand, CommandError

from accounts.constants import Role
from accounts.models import User
from tenants.constants import OrganizationType
from tenants.models import Organization

PLATFORM_ORG_NAME = "Platform"


class Command(BaseCommand):
    help = "Create (or update) the platform superadmin who can add organizations."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--full-name", default="Super Admin")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options["password"]
        if not password:
            raise CommandError("A password is required.")

        org, _ = Organization.objects.get_or_create(
            name=PLATFORM_ORG_NAME,
            defaults={"type": OrganizationType.INDIVIDUAL},
        )

        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_superuser(
                email=email,
                password=password,
                organization=org,
                role=Role.ORG_ADMIN,
                full_name=options["full_name"],
            )
            self.stdout.write(self.style.SUCCESS(f"Created superadmin: {email}"))
        else:
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated existing user to superadmin: {email}"))

        self.stdout.write("Log in with these credentials, then add organizations from the app.")
