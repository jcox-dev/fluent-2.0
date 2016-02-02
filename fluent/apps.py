

try:
    #Define a generator if model_mommy is available
    from model_mommy import generators

    def gen_translatablecontent():
        from fluent.fields import TranslatableContent
        return TranslatableContent(text=generators.gen_text())
except ImportError:
    pass


from django.apps import AppConfig

class FluentAppConfig(AppConfig):
    name = "fluent"

    def ready(self):
        from django.core.signals import request_finished, request_started
        from fluent.trans import ensure_threads_join, invalidate_caches_if_necessary
        request_finished.connect(ensure_threads_join, dispatch_uid="fluent.ensure_threads_join")
        request_started.connect(invalidate_caches_if_necessary, dispatch_uid="fluent.invalidate_caches_if_necessary")
