from rest_framework import status
from django.utils.translation import activate
from rest_framework import views
from rest_framework.response import Response
from django.contrib.auth import get_user_model
import django.apps
from django.utils.module_loading import import_string
from django.conf import settings
from ..serializers.serializer import get_serializer


model_list = []
for model in django.apps.apps.get_models():
    try:
        if model.is_for_page_view():
            model_list.append(model)
    except:  # noqa
        pass


languages_list = [x[0] for x in settings.LANGUAGES]


class PageApiView(views.APIView):

    @staticmethod
    def get_instance_by_slug(slug):
        for m in model_list:
            instance = m.objects.filter(slug=slug).first()
            if instance:
                return instance
        return None

    def get_object(self, slugs):
        print('slugs1', slugs)
        slug_list = slugs.split('/')
        slug = slug_list.pop(-1)
        obj = self.get_instance_by_slug(slug)
        return obj

    def get_permissions(self):
        permissions = [permission() for permission in self.permission_classes]
        page = self.get_object(self.kwargs.get('slugs'))
        if page:
            page_permissions = page.get_permissions()
            if page_permissions:
                permissions = [permission() for permission in page_permissions]
        return permissions

    def get(self, request, slugs):
        language = languages_list[0]
        if 'HTTP_ACCEPT_LANGUAGE' in request.META and request.META['HTTP_ACCEPT_LANGUAGE'] in languages_list:
            language = request.META['HTTP_ACCEPT_LANGUAGE']
        activate(language)

        page = self.get_object(slugs)

        if request.user.is_authenticated:
            user = get_user_model().objects.get(pk=request.user.pk)
        else:
            user = None

        if page is None:
            data = {
                'page_model': None,
                'init_state': {}
            }
            return Response(data, status=status.HTTP_404_NOT_FOUND)

        page_context = page.get_context(request, object=page, user=user)
        page_context.pop('request')
        for k, v in page_context.items():
            if hasattr(v, 'is_for_page_view'):
                model_serializer_class = get_serializer(v.__class__)
                page_context[k] = model_serializer_class(v).data
        if 'paginated_object_list' in page_context:
            page_context['paginated_object_list'] = list({'id': x.id, 'title': x.title, 'get_absolute_url': x.get_absolute_url()} for x in page_context['paginated_object_list'])
        if 'paginator' in page_context:
            page_context['num_pages'] = page_context['paginator'].num_pages
            page_context['per_page'] = page_context['paginator'].per_page
            page_context.pop('paginator')

        page_context['global'] = import_string(settings.GARPIX_PAGE_GLOBAL_CONTEXT)(request, page)
        data = {
            'page_model': page.__class__.__name__,
            'init_state': page_context,
        }
        return Response(data)
