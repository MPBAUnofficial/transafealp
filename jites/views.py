# Create your views here.
from django.utils import timezone
from django.db import transaction, connection, DatabaseError
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
import json
from django.views.decorators.csrf import csrf_exempt
from scenario.models import Scenario, ScenarioSubcategory
from django.views.generic.detail import BaseDetailView
from mixin import LoginRequiredMixin, JSONResponseMixin
from .models import Event, EvMessage, EvAction, EvActionGraph, EvVisualization, EvActor
from scenario.utility import Membership
from .utility import make_tree, Actor_Action_Association, SetEncoder, actiondetail_json


@login_required
def dashboard(request, displaymode, event_id):
    context = {
        'displaymode': displaymode,
        'event_id': event_id,
        'username': request.user
    }

    return render_to_response('jites/dashboard.html', context, context_instance=RequestContext(request))


@login_required
def poll(request):
    # TODO implemented by real request on scenario log table. This is a demo.
    result = ({
                  'type': 'event',
                  'name': 'log',
                  'data': {
                      'id': request.user.id,
                      'type': 'SYSTEM',
                      'ts': timezone.now().strftime("%d/%m/%y %H:%M:%S.%f"),
                      'username': str(request.user),
                      'msg': 'System ready to accept connections'
                  }
              }, {
                  'type': 'event',
                  'name': 'log',
                  'data': {
                      'id': request.user.id,
                      'type': 'TASK',
                      'ts': timezone.now().strftime("%d/%m/%y %H:%M:%S.%f"),
                      'username': str(request.user),
                      'msg': 'New event <strong>CP/FF/10</strong>'
                  }
              })
    j = json.dumps(result)
    return HttpResponse(j, content_type="application/json")


@login_required
def select_event_location(request, scenario_id, type):
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name, subcategory_id, description, ST_AsGeoJSON(ST_Transform(geom,900913)) FROM scenario WHERE id=%s",
            [scenario_id])

    except DatabaseError, e:
        transaction.rollback()
        return HttpResponse(str(e))

    row = cursor.fetchone()
    cursor.close()

    category = ScenarioSubcategory.objects.get(pk=int(list(row)[1]))
    geometry = list(row)[3]
    context = {'scenario': list(row), 'scenario_id': scenario_id, 'category': category, 'geometry': geometry,
               'type': type}
    return render_to_response('jites/select_event_location.html', context, context_instance=RequestContext(request))


@login_required
def start_event(request, scenario_id, type):
    point = request.GET['point']
    scenario = Scenario.objects.get(pk=scenario_id)

    if type == 'simulation':
        is_real = True
        pass
    elif type == 'emergency':
        is_real = False
        pass

    geom = 'SRID=900913;POINT({0})'.format(point)

    try:
        cursor = connection.cursor()
        cursor.execute(
            "select * from start_event(%s,%s,ST_Transform(%s::geometry,3035));",
            [scenario.name, is_real, geom])
    except DatabaseError, e:
        transaction.rollback()
        return HttpResponse(str(e))

    row = cursor.fetchone()
    cursor.close()

    result = {
        'success': True,
        'event_id': list(row)[0]
    }

    j = json.dumps(result)

    return HttpResponse(j, content_type="application/json")


#class based view for json render Event (in the url: /jites/get_event/<idevent>)
class EventDetailView(LoginRequiredMixin, JSONResponseMixin, BaseDetailView):
    model = Event

    def get(self, request, *args, **kwargs):
        qs = Event.objects.get(pk=kwargs['pk'])

        try:
            cursor = connection.cursor()
            cursor.execute(
                'select '
                'ST_X(ST_Transform(event_geom,900913)) as event_x,'
                'ST_Y(ST_Transform(event_geom,900913)) as event_y '
                'from event where id = %s',
                [kwargs['pk']])
        except DatabaseError, e:
            transaction.rollback()
            return HttpResponse(str(e))

        row = cursor.fetchone()
        cursor.close()

        dict = {'data': {'status': qs.status,
                         'subcategory_name': qs.subcategory_name,
                         'event_name': qs.event_name,
                         'is_real': qs.is_real,
                         'category_name': qs.category_name,
                         'event_description': qs.event_description,
                         'time_start': str(qs.time_start),
                         'lon': row[0],
                         'lat': row[1]
        },
                'success': 'true'
        }

        json_response = json.dumps(dict, separators=(',', ':'), sort_keys=True)
        return HttpResponse(json_response, mimetype='application/json;')


#class based view for json render Action (in the url: /jites/get_action/<idevent>)
class ActionDetailView(LoginRequiredMixin, JSONResponseMixin, BaseDetailView):
    model = EvAction

    def get(self, request, *args, **kwargs):
        try:
            cursor = connection.cursor()
            cursor.execute(
                'select *'
                ' from '
                'ev_action_next_status(%s)',
                [kwargs['pk']])
        except DatabaseError, e:
            transaction.rollback()
            return HttpResponse(str(e))

        row = cursor.fetchone()
        cursor.close()

        action = EvAction.objects.get(pk=kwargs['pk'])
        actors = Actor_Action_Association(request.user, action.event.pk,
                                          action.pk).actors_already_assigned_to_this_action()
        actors_list = EvActor.objects.filter(pk__in=[l.actor.id for l in actors])
        visualizations = EvVisualization.objects.filter(action=action)
        act = []
        for a in actors_list:
            act.append({
                'name': a.name,
                'istitution': a.istitution,
                'contact_info': a.contact_info,
                'email': a.email,
                'phone': a.phone,
            })
        vis = []
        for v in visualizations:
            vis.append({
                'description': v.description,
                'type': v.type,
                'resource': v.resource,
                'options': v.options
            })
        action_detail = {
            'success': True,
            'data': {
                'action': {
                    'pk': action.pk,
                    'name': action.name,
                    'numcode': action.numcode,
                    'description': action.description,
                    'duration': action.duration,
                    'status': action.status,
                    'comment': action.comment,
                    'next_status': row[0],
                    'next_status_reason': row[1],
                },
                'actors': act,
                'visualization': vis
            }
        }

        json_response = json.dumps(action_detail, separators=(',', ':'), sort_keys=True, cls=SetEncoder)
        return HttpResponse(json_response, mimetype='application/json;')

#standard view for adding message to event
@login_required()
def update_action_status(request, pk):
    action = EvAction.objects.get(pk=pk)
    if request.method == "POST" and request.is_ajax():
        action.status = request.POST['status']
        action.comment = request.POST['content']
        action.save()

        #in action_detail ha il json che ti serve
        action_detail = actiondetail_json(request.user, pk)

        msg = {
            "success": True,
            "data": action_detail
        }

    else:
        msg = {
            "success": False,
            "message": "GET request are not allowed for this view."
        }

    json_response = json.dumps(msg, separators=(',', ':'), sort_keys=True, cls=SetEncoder)
    return HttpResponse(json_response, mimetype="application/json;")

#standard view for adding message to event
@login_required()
def save_event_message(request, event_id):
    event = Event.objects.get(pk=event_id)
    ts = timezone.now()
    username = request.user
    if request.method == "POST" and request.is_ajax():
        if request.POST['content']:
            message_to_save = EvMessage(event=event, ts=ts, username=username, content=request.POST['content'])
            message_to_save.save()
            msg = {
                "success": True
            }
        else:
            msg = {
                "success": False,
                "message": "Form is invalid"
            }
    else:
        msg = {
            "success": False,
            "message": "GET request are not allowed for this view."
        }

    json_response = json.dumps(msg)
    return HttpResponse(json_response, mimetype="application/json;")


@login_required
def tree_to_json(request, event_id):
    event = Event.objects.get(pk=event_id, managing_authority=Membership(request.user).membership_auth)
    root_action = EvAction.objects.get(event=event, name='root')
    actions = EvActionGraph.objects.filter(action__event=event, parent__event=event, is_main_parent=True)
    pc = ([])
    pc.append([root_action.id,
               root_action.id,
               root_action.name,
               root_action.numcode,
               root_action.description,
               root_action.duration,
               root_action.status,
               root_action.comment
    ])
    for action in actions:
        pc.append([action.parent.id,
                   action.action.id,
                   action.action.name,
                   action.action.numcode,
                   action.action.description,
                   action.action.duration,
                   action.action.status,
                   action.action.comment
        ])

    tree = make_tree(pc, root_action.id)
    json_response = json.dumps(dict(tree))

    return HttpResponse(json_response, mimetype='text/javascript;')


@csrf_exempt
@login_required
def proxy(request):
    import httplib2

    conn = httplib2.Http()

    url = request.GET['url']
    if request.method == 'GET':
        response, content = conn.request(url, request.method)

    return HttpResponse(content, status=int(response['status']), mimetype=response['content-type'])
