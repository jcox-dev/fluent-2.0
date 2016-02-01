from django.contrib import admin
from django.shortcuts import render
from django.conf.urls import patterns, url

from fluent.models import MasterTranslation, Translation


def scan_view(request):
    subs = {}

    if request.method == "POST":
        pass
    else:
        pass

    return render(request, "fluent/scan.html", subs)


class MasterTranslationAdmin(admin.ModelAdmin):

    def get_urls(self):
        urls = super(MasterTranslationAdmin, self).get_urls()

        urls = patterns('',
            url(r'scan/$', scan_view, name="fluent_translation_scan"),
        ) + urls

        return urls

admin.site.register(MasterTranslation, MasterTranslationAdmin)
admin.site.register(Translation)
