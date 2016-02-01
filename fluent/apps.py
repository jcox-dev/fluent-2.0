

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
