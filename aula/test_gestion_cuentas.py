from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from .models import AccesoCurso, Curso, Inscripcion, Perfil
from .permisos import permisos

User = get_user_model()


class GestionCuentasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = User.objects.create_superuser('direccion', password='Local-test-789!')
        cls.gestora = User.objects.create_user('gestora')
        cls.permiso = Permission.objects.get(content_type__app_label='aula', codename='gestionar_cuentas')
        cls.gestora.user_permissions.add(cls.permiso)
        cls.alumno = User.objects.create_user('alumno', first_name='Ana', last_name='Prueba')
        cls.curso = Curso.objects.create(titulo='Curso local', publicado=True)
        cls.inscripcion = Inscripcion.objects.create(curso=cls.curso, cursante=cls.alumno)
        Perfil.objects.create(usuario=cls.alumno, dni='RESERVADO', sacramentos='PRIVADO')

    def setUp(self):
        self.client.force_login(self.gestora)

    def datos(self, **extra):
        return {'curso': self.curso.pk, 'username': 'nueva', 'first_name': 'Maria',
                'last_name': 'Prueba', 'password1': 'Clave-local-789!',
                'password2': 'Clave-local-789!', 'rol': 'cursante', 'dias_cortesia': 30, **extra}

    def test_create_enroll_force_password_change_without_elevation(self):
        r = self.client.post(reverse('aula:usuario_nuevo'), self.datos(
            is_staff='on', is_superuser='on', user_permissions=[self.permiso.pk], emitir='on'))
        persona = User.objects.get(username='nueva')
        self.assertRedirects(r, reverse('aula:usuario', args=[persona.pk]))
        self.assertFalse(persona.is_staff or persona.is_superuser)
        self.assertFalse(persona.user_permissions.exists() or persona.groups.exists())
        self.assertTrue(persona.perfil_aula.cambiar_clave)
        self.assertTrue(Inscripcion.objects.filter(cursante=persona, curso=self.curso).exists())
        acceso = AccesoCurso.objects.get(usuario=persona)
        self.assertEqual(acceso.dias, 30)
        self.assertIsNone(acceso.inicio)
        self.assertTrue(persona.check_password('Clave-local-789!'))
        self.assertFalse(LogEntry.objects.filter(change_message__contains='Clave-local').exists())

    def test_formador_cannot_validate_issue_or_delegate(self):
        r = self.client.post(reverse('aula:usuario_nuevo'), self.datos(rol='formador'))
        self.assertEqual(r.status_code, 302)
        persona = User.objects.get(username='nueva')
        reglas = permisos(persona, self.curso)
        self.assertTrue(reglas['corregir'] and reglas['responder_foro'])
        self.assertFalse(reglas['emitir'] or reglas['validar'] or reglas['disenar'] or reglas['moderar_foro'])
        self.assertFalse(persona.has_perm('aula.gestionar_cuentas'))

    def test_disable_and_reactivate_preserve_history_and_invalidate_session(self):
        alumno_client = Client()
        alumno_client.force_login(self.alumno)
        url = reverse('aula:usuario', args=[self.alumno.pk])
        self.assertEqual(self.client.post(url, {'accion': 'desactivar'}).status_code, 302)
        self.alumno.refresh_from_db()
        self.assertFalse(self.alumno.is_active)
        self.assertTrue(Inscripcion.objects.filter(pk=self.inscripcion.pk).exists())
        self.assertEqual(alumno_client.get(reverse('aula:perfil')).status_code, 302)
        self.client.post(url, {'accion': 'activar'})
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.is_active)
        self.assertEqual(LogEntry.objects.filter(user=self.gestora, object_id=str(self.alumno.pk)).count(), 2)

    def test_privileged_accounts_and_self_protected_even_if_inactive(self):
        staff = User.objects.create_user('editor', is_staff=True)
        delegada = User.objects.create_user('otra_gestora', is_active=False)
        delegada.user_permissions.add(self.permiso)
        grupo = Group.objects.create(name='Gestion')
        grupo.permissions.add(self.permiso)
        miembro = User.objects.create_user('miembro')
        miembro.groups.add(grupo)
        for persona in (self.director, self.gestora, staff, delegada, miembro):
            for accion in ('activar', 'desactivar', 'eliminar'):
                with self.subTest(usuario=persona.username, accion=accion):
                    self.assertEqual(self.client.post(reverse('aula:usuario', args=[persona.pk]),
                        {'accion': accion, 'confirmacion': persona.username}).status_code, 403)
        delegada.refresh_from_db()
        self.assertFalse(delegada.is_active)

    def test_cannot_delete_any_account_or_change_access_period(self):
        vacia = User.objects.create_user('sin_historia')
        self.assertEqual(self.client.post(reverse('aula:usuario', args=[vacia.pk]),
            {'accion': 'eliminar', 'confirmacion': vacia.username}).status_code, 403)
        self.assertTrue(User.objects.filter(pk=vacia.pk).exists())
        self.assertEqual(self.client.post(reverse('aula:usuario_acceso', args=[self.alumno.pk, self.curso.pk]),
            {'dias': 99}).status_code, 403)

    def test_other_management_and_private_profile_stay_closed(self):
        urls = [reverse('aula:gestion'), reverse('aula:usuarios_importar'), reverse('aula:accesos_iniciales'),
                reverse('aula:gestion_curso', args=[self.curso.pk]),
                reverse('aula:gestion_persona_nueva', args=[self.curso.pk])]
        for url in urls:
            for method in ('get', 'post'):
                with self.subTest(url=url, method=method):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:auth_user_change', args=[self.alumno.pk])).status_code, 302)
        r = self.client.get(reverse('aula:usuario', args=[self.alumno.pk]))
        self.assertNotContains(r, 'RESERVADO')
        self.assertNotContains(r, 'PRIVADO')
        self.assertNotContains(r, 'Eliminar definitivamente')
        self.assertNotContains(r, 'Configurar plazo')

    def test_navigation_and_form_are_available_without_staff(self):
        r = self.client.get(reverse('aula:panel'))
        self.assertContains(r, reverse('aula:usuarios'))
        r = self.client.get(reverse('aula:usuarios'))
        self.assertContains(r, 'Crear una cuenta')
        self.assertNotContains(r, 'Crear cuentas en lote')
        self.assertNotContains(r, 'Simplificar usuarios')
        r = self.client.get(reverse('aula:usuario_nuevo'))
        self.assertContains(r, 'Crear cuenta y agregar al curso')
        self.assertIn('no-store', r['Cache-Control'])

    def test_missing_permission_revocation_inactive_and_csrf_denied(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.gestora)
        self.assertEqual(csrf.post(reverse('aula:usuario_nuevo'), self.datos()).status_code, 403)
        self.gestora.user_permissions.clear()
        for url in (reverse('aula:usuarios'), reverse('aula:usuario_nuevo'), reverse('aula:usuario', args=[self.alumno.pk])):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, self.datos()).status_code, 403)
        self.gestora.user_permissions.add(self.permiso)
        self.gestora.is_active = False
        self.gestora.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(reverse('aula:usuarios')).status_code, 302)

    def test_existing_user_password_not_overwritten_and_invalid_role_rejected(self):
        original = self.alumno.password
        self.assertEqual(self.client.post(reverse('aula:usuario_nuevo'), self.datos(username='alumno')).status_code, 200)
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.password, original)
        self.assertEqual(self.client.post(reverse('aula:usuario_nuevo'), self.datos(rol='administrador')).status_code, 200)
        self.assertFalse(User.objects.filter(username='nueva').exists())

    def test_direction_keeps_existing_capabilities(self):
        self.client.force_login(self.director)
        self.assertContains(self.client.get(reverse('aula:usuarios')), 'Crear cuentas en lote')
        self.assertEqual(self.client.get(reverse('aula:usuario_nuevo')).status_code, 200)
        self.assertEqual(self.client.post(reverse('aula:usuario', args=[self.gestora.pk]),
            {'accion': 'desactivar'}).status_code, 302)
