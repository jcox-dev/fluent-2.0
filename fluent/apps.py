

try:
    # Configure a generator if the user is using model_mommy

    from model_mommy import generators

    def gen_translatablecontent(max_length):
        from fluent.fields import TranslatableContent
        return TranslatableContent(text=generators.gen_string(max_length))
    gen_translatablecontent.required = ['max_length']

    MOMMY_CUSTOM_FIELDS_GEN = {
        'fluent.fields.TranslatableField': gen_translatablecontent,
    }
except ImportError:
    pass


from django.apps import AppConfig

class FluentAppConfig(AppConfig):
    name = "fluent"
