# Copyright (c) 2017 Red Hat, Inc
from django.shortcuts import render
from django import forms
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse, HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
import yaml

import json


# Create your views here.
from .models import Topology, FSMTrace, EventTrace, TopologySnapshot
from .models import TestCase
from .serializers import topology_data


def index(request):
    return render(request, "network_ui/index.html", dict(topologies=Topology.objects.all().order_by('-pk')))


class TopologyForm(forms.Form):
    topology_id = forms.IntegerField()


def json_topology_data(request):
    form = TopologyForm(request.GET)
    if form.is_valid():
        return JsonResponse(topology_data(form.cleaned_data['topology_id']))
    else:
        return HttpResponseBadRequest(form.errors)


def yaml_topology_data(request):
    form = TopologyForm(request.GET)
    if form.is_valid():
        return HttpResponse(yaml.safe_dump(topology_data(form.cleaned_data['topology_id']),
                                           default_flow_style=False),
                            content_type='application/yaml')
    else:
        return HttpResponseBadRequest(form.errors)


class FSMTraceForm(forms.Form):
    topology_id = forms.IntegerField()
    trace_id = forms.IntegerField()
    client_id = forms.IntegerField()


def download_trace(request):
    form = FSMTraceForm(request.GET)
    if form.is_valid():
        topology_id = form.cleaned_data['topology_id']
        trace_id = form.cleaned_data['trace_id']
        client_id = form.cleaned_data['client_id']
        data = list(FSMTrace.objects.filter(trace_session_id=trace_id,
                                            client_id=client_id).order_by('order').values())
        response = HttpResponse(yaml.safe_dump(data, default_flow_style=False),
                                content_type="application/force-download")
        response['Content-Disposition'] = 'attachment; filename="trace_{0}_{1}_{2}.yml"'.format(topology_id, client_id, trace_id)
        return response
    else:
        return HttpResponse(form.errors)


class RecordingForm(forms.Form):
    topology_id = forms.IntegerField()
    trace_id = forms.IntegerField()
    client_id = forms.IntegerField()


def download_recording(request):
    form = RecordingForm(request.GET)
    if form.is_valid():
        topology_id = form.cleaned_data['topology_id']
        trace_id = form.cleaned_data['trace_id']
        client_id = form.cleaned_data['client_id']
        data = dict()
        data['event_trace'] = [json.loads(x) for x in EventTrace
                               .objects.filter(trace_session_id=trace_id, client_id=client_id)
                               .order_by('message_id')
                               .values_list('event_data', flat=True)]
        data['fsm_trace'] = list(FSMTrace
                                 .objects
                                 .filter(trace_session_id=trace_id, client_id=client_id)
                                 .order_by('order')
                                 .values())
        data['snapshots'] = [json.loads(x) for x in TopologySnapshot
                             .objects.filter(trace_session_id=trace_id, client_id=client_id)
                             .order_by('order')
                             .values_list('snapshot_data', flat=True)]
        response = HttpResponse(json.dumps(data, sort_keys=True, indent=4),
                                content_type="application/force-download")
        response['Content-Disposition'] = 'attachment; filename="trace_{0}_{1}_{2}.yml"'.format(topology_id, client_id, trace_id)
        return response
    else:
        return HttpResponse(form.errors)


def tests(request):
    tests = TestCase.objects.all().values('test_case_id', 'name')
    return render(request, 'network_ui/tests.html', dict(tests=tests))


def create_test(name, data):
    try:
        test_case = TestCase.objects.get(name=name)
        test_case.test_case_data=json.dumps(data)
        test_case.save()
    except ObjectDoesNotExist:
        TestCase(name=name, test_case_data=json.dumps(data)).save()


class UploadTestForm(forms.Form):
    name = forms.CharField()
    file = forms.FileField()


def upload_test(request):
    if request.method == 'POST':
        form = UploadTestForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data['name']
            data = json.loads(request.FILES['file'].read())
            create_test(name, data)
            return HttpResponseRedirect('/network_ui/tests')
    else:
        form = UploadTestForm()
    return render(request, 'network_ui/upload_test.html', {'form': form})
