from django.contrib import admin
from django.shortcuts import render, redirect
from django.conf.urls import url

from djangae.db import transaction

from google.appengine.ext.deferred import defer

from fluent.models import MasterTranslation, Translation, ScanMarshall
from fluent.scanner import begin_scan


def scan_view(request):
    subs = {}

    marshall = ScanMarshall.objects.first()
    if request.method == "POST":
        if not marshall:
            with transaction.atomic():
                marshall = ScanMarshall.objects.create()
                defer(begin_scan, marshall, _transactional=True)
        return redirect("admin:fluent_translation_scan")

    subs["marshall"] = marshall

    return render(request, "fluent/scan.html", subs)


class MasterTranslationAdmin(admin.ModelAdmin):

    def get_urls(self):
        return super(MasterTranslationAdmin, self).get_urls() + [
            url(r'scan/$', scan_view, name="fluent_translation_scan"),
        ]


admin.site.register(MasterTranslation, MasterTranslationAdmin)
admin.site.register(Translation)
