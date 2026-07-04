from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.constants import Role
from accounts.models import User
from attempts.models import Attempt
from attempts.services.grading import grade
from materials.models import SourceMaterial
from materials.services.ingestion import ingest
from questions.constants import Difficulty, QuestionCategory
from questions.models import Question
from questions.services.generation import generate_for_material
from tenants.constants import OrganizationType, PrepContext
from tenants.context import tenant_context
from tenants.models import Organization

DEMO_PASSWORD = "Prep@1234"

# Short but real-enough source texts (repeated so they chunk into a couple pieces).
EXAM_SOURCES = {
    "Cell Biology": (
        "The cell is the basic unit of life. Prokaryotic cells lack a nucleus while "
        "eukaryotic cells contain a membrane-bound nucleus. Mitochondria produce ATP "
        "through cellular respiration. The cell membrane controls what enters and leaves. "
    ) * 5,
    "Genetics": (
        "Genes are segments of DNA that code for proteins. Alleles are alternative forms "
        "of a gene. Dominant alleles mask recessive ones. A Punnett square predicts the "
        "probability of offspring genotypes from two parents. "
    ) * 5,
    "Photosynthesis": (
        "Photosynthesis converts light energy into chemical energy stored in glucose. It "
        "occurs in chloroplasts and requires carbon dioxide and water, releasing oxygen. "
        "The light reactions and the Calvin cycle are its two stages. "
    ) * 5,
}
INTERVIEW_SOURCES = {
    "System Design": (
        "The backend engineer designs scalable services. Responsibilities include API "
        "design, database schema design, caching, rate limiting, and handling high "
        "throughput with reliability and observability. "
    ) * 5,
    "Databases": (
        "Strong SQL and relational modelling are required. The candidate should understand "
        "indexing, transactions, isolation levels, query optimisation, and when to use "
        "normalisation versus denormalisation. "
    ) * 5,
    "Behavioral": (
        "We value ownership, collaboration, and clear communication. Candidates should "
        "describe past conflicts, how they handled ambiguity, and how they mentor peers "
        "and give feedback. "
    ) * 5,
}


class Command(BaseCommand):
    help = "Seed demo tenants (2 schools + company + institute) with users, questions, attempts."

    @transaction.atomic
    def handle(self, *args, **options):
        self._wipe_previous()

        schools = [
            ("Springfield High", ["Homer", "Lisa", "Bart"]),
            ("Riverdale High", ["Archie", "Betty", "Jughead"]),
        ]
        for name, student_names in schools:
            self._seed_school(name, student_names)

        self._seed_interview_tenant(
            "Acme Corp", OrganizationType.COMPANY, ["Dana", "Ravi", "Mei"]
        )
        self._seed_interview_tenant(
            "CodeCoach Institute", OrganizationType.INSTITUTE, ["Sam", "Priya", "Leo"]
        )

        self._print_summary()

    # ------------------------------------------------------------------ helpers

    def _wipe_previous(self):
        names = ["Springfield High", "Riverdale High", "Acme Corp", "CodeCoach Institute"]
        deleted = Organization.objects.filter(name__in=names)
        if deleted.exists():
            # Cascades to users, materials, chunks, questions, attempts.
            deleted.delete()
            self.stdout.write("Cleared previous demo data.")

    def _make_user(self, org, role, first_name, linked=None):
        email = f"{first_name.lower()}@{org.name.split()[0].lower()}.demo"
        return User.objects.create_user(
            email=email,
            password=DEMO_PASSWORD,
            organization=org,
            role=role,
            full_name=first_name,
            linked_learner=linked,
        )

    def _seed_school(self, name, student_names):
        org = Organization.objects.create(name=name, type=OrganizationType.SCHOOL)
        self._make_user(org, Role.ORG_ADMIN, "Admin")
        teacher = self._make_user(org, Role.TEACHER, "Teacher")
        students = [self._make_user(org, Role.STUDENT, n) for n in student_names]
        # One parent linked to the first student (observer demo).
        self._make_user(org, Role.PARENT, "Parent", linked=students[0])

        topics = list(EXAM_SOURCES.items())
        self._seed_content(
            org,
            teacher,
            students,
            mode=PrepContext.EXAM,
            subject="Biology",
            topic_sources=topics,
            tag_kwargs={"difficulty": Difficulty.MEDIUM},
        )
        self.stdout.write(self.style.SUCCESS(f"Seeded school: {name}"))

    def _seed_interview_tenant(self, name, org_type, candidate_names):
        org = Organization.objects.create(name=name, type=org_type)
        self._make_user(org, Role.ORG_ADMIN, "Admin")
        mentor = self._make_user(org, Role.MENTOR, "Mentor")
        candidates = [self._make_user(org, Role.CANDIDATE, n) for n in candidate_names]

        topics = list(INTERVIEW_SOURCES.items())
        self._seed_content(
            org,
            mentor,
            candidates,
            mode=PrepContext.INTERVIEW,
            subject="Backend Engineer",
            topic_sources=topics,
            tag_kwargs={"category": QuestionCategory.TECHNICAL},
        )
        self.stdout.write(self.style.SUCCESS(f"Seeded interview tenant: {name}"))

    def _seed_content(self, org, uploader, learners, *, mode, subject, topic_sources, tag_kwargs):
        with tenant_context(org):
            materials = []
            for topic, text in topic_sources:
                material = SourceMaterial.objects.create(
                    mode=mode,
                    subject_or_role=subject,
                    topic=topic,
                    source_text=text,
                    uploaded_by=uploader,
                )
                ingest(material)  # parse -> chunk -> embed -> READY
                generate_for_material(material, count=4, **tag_kwargs)
                materials.append(material)

            strong_material, weak_material = materials[0], materials[1]
            for learner in learners:
                self._answer(learner, strong_material, well=True)
                self._answer(learner, weak_material, well=False)

    def _answer(self, learner, material, *, well):
        questions = Question.objects.filter(source_material=material)[:3]
        for q in questions:
            submitted = q.reference_answer if well else "I am not sure about this."
            attempt = Attempt.objects.create(
                learner=learner, question=q, submitted_answer=submitted
            )
            grade(attempt)

    def _print_summary(self):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Demo data ready. Login credentials:"))
        self.stdout.write(f"  Password for ALL demo users: {DEMO_PASSWORD}")
        self.stdout.write("  Exam mode (schools):")
        self.stdout.write("    teacher@springfield.demo  (TEACHER, sees all students)")
        self.stdout.write("    homer@springfield.demo    (STUDENT)")
        self.stdout.write("    parent@springfield.demo   (PARENT, linked to Homer)")
        self.stdout.write("    admin@riverdale.demo      (ORG_ADMIN of the OTHER school)")
        self.stdout.write("  Interview mode:")
        self.stdout.write("    mentor@acme.demo          (MENTOR, sees all candidates)")
        self.stdout.write("    dana@acme.demo            (CANDIDATE)")
        self.stdout.write("    mentor@codecoach.demo     (MENTOR of the institute tenant)")
        self.stdout.write("")
        self.stdout.write(
            "Isolation demo: log in as teacher@springfield.demo and note you cannot see "
            "any Riverdale/Acme/CodeCoach data via the API."
        )
