"""Contenido privado y corrección en servidor; nunca se acepta una nota del navegador."""
import copy
import random
import json
import unicodedata
from uuid import uuid4
from django.core.exceptions import ValidationError
from core import models as juegos

FUENTES = {'trivia': juegos.Trivia, 'ordenar': juegos.OrdenaPasos,
           'memoria': juegos.JuegoMemoria, 'palabra': juegos.JuegoPalabraSecreta,
           'camino': juegos.EligeCamino, 'ruleta': juegos.RuletaDesafio}


def normalizar(texto):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', str(texto).casefold())
                           if not unicodedata.combining(c)).split())


def importar(prueba, juego):
    from .models import ItemPrueba
    filas = []
    if prueba.tipo == 'trivia':
        for pregunta in juego.preguntas.prefetch_related('opciones'):
            opciones = list(pregunta.opciones.all())
            correctas = [i + 1 for i, opcion in enumerate(opciones) if opcion.es_correcta]
            if len(correctas) != 1 or len(opciones) < 2:
                raise ValidationError('Cada pregunta de la trivia debe tener una única opción correcta y al menos dos opciones.')
            filas.append((pregunta.texto, [o.texto for o in opciones], str(correctas[0])))
    elif prueba.tipo == 'ordenar':
        for etapa in juego.etapas.filter(activo=True).prefetch_related('pasos'):
            pasos = [p.texto for p in etapa.pasos.all()]
            if len(pasos) >= 2:
                filas.append((etapa.titulo, pasos, ''))
    elif prueba.tipo == 'memoria':
        filas = [(p.concepto, [], p.relacion) for p in juego.parejas.all()]
    elif prueba.tipo == 'palabra':
        filas = [(p.pista, [], p.palabra) for p in juego.palabras.all()]
    elif prueba.tipo == 'ruleta':
        filas = [(p.texto, [], '') for p in juego.sectores.filter(activo=True)]
    elif prueba.tipo == 'camino':
        escenas = list(juego.escenas.filter(activo=True).prefetch_related('opciones'))
        ids = {e.pk for e in escenas}
        inicios = [e for e in escenas if e.es_inicio]
        if len(inicios) != 1:
            raise ValidationError('El camino necesita exactamente una escena de inicio.')
        grafo = {str(e.pk): {'texto': e.titulo + '\n' + e.texto, 'final': e.es_final,
            'resultado': e.tipo_final, 'opciones': [{'id': str(o.pk), 'texto': o.texto_opcion, 'destino': str(o.escena_destino_id)}
                for o in e.opciones.filter(activo=True) if o.escena_destino_id in ids]} for e in escenas}
        vistos, pendientes = set(), [str(inicios[0].pk)]
        while pendientes:
            nodo = pendientes.pop()
            if nodo in vistos:
                continue
            vistos.add(nodo)
            pendientes.extend(o['destino'] for o in grafo[nodo]['opciones'])
        if not any(grafo[n]['final'] for n in vistos) or any(not grafo[n]['final'] and not grafo[n]['opciones'] for n in vistos):
            raise ValidationError('Revisá el camino: debe llegar a un final y no tener escenas sin salida.')
        if inicios[0].es_final:
            raise ValidationError('El camino necesita una decisión antes del final.')
        no_finales=[inicios[0]]+[e for e in escenas if not e.es_final and e.pk!=inicios[0].pk]
        if len(no_finales)>100 or any(e.es_final and e.tipo_final not in {'bueno','neutro','malo'} for e in escenas):
            raise ValidationError('Usá hasta 100 escenas y definí el resultado de cada final.')
        mapa={str(e.pk):uuid4() for e in no_finales}
        for orden,e in enumerate(no_finales,1):
            opciones=grafo[str(e.pk)]['opciones']
            destinos=[('final_'+grafo[o['destino']]['resultado']) if grafo[o['destino']]['final'] else str(mapa[o['destino']]) for o in opciones]
            ItemPrueba.objects.create(id=mapa[str(e.pk)],prueba=prueba,texto=e.titulo+'\n'+e.texto,
                opciones=[o['texto'] for o in opciones],respuesta=json.dumps({'destinos':destinos}),orden=orden)
        return
    if not filas:
        raise ValidationError('El juego todavía no tiene actividades utilizables. Agregá contenido al juego o creá una prueba nueva.')
    if len(filas) > 100:
        raise ValidationError('Importá hasta 100 actividades por prueba.')
    ItemPrueba.objects.bulk_create([ItemPrueba(prueba=prueba, texto=t, opciones=o, respuesta=r, orden=i)
                                    for i, (t, o, r) in enumerate(filas, 1)])


def preparar(prueba):
    datos = copy.deepcopy(prueba.contenido)
    datos['tipo'] = prueba.tipo
    datos['titulo'] = prueba.leccion.titulo
    datos['instrucciones'] = prueba.instrucciones
    if datos.get('grafo'):
        return datos
    if prueba.tipo == 'rompecabezas':
        from .models import RecursoLeccion
        if not datos.get('imagen') or not RecursoLeccion.objects.filter(pk=datos['imagen'],leccion=prueba.leccion,tipo='imagen',activo=True).exists():
            raise ValidationError('Primero elegí una imagen para el rompecabezas.')
        tokens = [uuid4().hex for _ in range(9)]
        datos['solucion'] = tokens
        datos['piezas'] = [{'id': token, 'x': (i % 3) * 50, 'y': (i // 3) * 50} for i, token in enumerate(tokens)]
        random.SystemRandom().shuffle(datos['piezas'])
        return datos
    items = list(prueba.items.filter(activo=True))
    if not items:
        raise ValidationError('Esta prueba todavía está en preparación.')
    if prueba.tipo=='camino':
        grafo={}
        for resultado in ['bueno','neutro','malo']:
            grafo['final_'+resultado]={'texto':'Llegaste al final del recorrido.','final':True,'resultado':resultado,'opciones':[]}
        for n,item in enumerate(items):
            try:
                destinos=json.loads(item.respuesta)['destinos']
            except (ValueError,KeyError,TypeError):
                raise ValidationError('Revisá los destinos de cada escena del camino.')
            if len(destinos)!=len(item.opciones):
                raise ValidationError('Cada decisión debe tener un destino.')
            opciones=[]
            for texto,destino in zip(item.opciones,destinos):
                if destino=='siguiente':
                    if n+1>=len(items):
                        raise ValidationError('La última escena debe terminar en un final; no tiene una escena siguiente.')
                    destino=str(items[n+1].pk)
                opciones.append({'id':uuid4().hex,'texto':texto,'destino':destino})
            grafo[str(item.pk)]={'texto':item.texto,'final':False,'resultado':'','opciones':opciones}
        # Toda escena debe poder alcanzar un final: evita recorridos sin salida.
        alcanzan={k for k,v in grafo.items() if v['final']}
        for _ in grafo:
            alcanzan.update(k for k,v in grafo.items() if any(o['destino'] in alcanzan for o in v['opciones']))
        if any(o['destino'] not in grafo for v in grafo.values() for o in v['opciones']) or len(alcanzan)!=len(grafo):
            raise ValidationError('Revisá el camino: hay destinos inexistentes o escenas que no pueden llegar a un final.')
        datos.update(grafo=grafo,inicio=str(items[0].pk))
        return datos
    if prueba.tipo == 'ruleta':
        items = [random.SystemRandom().choice(items)]
    datos['preguntas'] = []
    relaciones = [{'id': str(item.pk), 'texto': item.respuesta} for item in items]
    random.SystemRandom().shuffle(relaciones)
    for item in items:
        p = {'id': str(item.pk), 'texto': item.texto, 'respuesta': item.respuesta}
        if prueba.tipo in {'trivia', 'camino', 'ordenar'}:
            opciones = [{'id': uuid4().hex, 'texto': texto} for texto in item.opciones]
            if prueba.tipo in {'trivia', 'camino'}:
                try:
                    if not 1<=int(item.respuesta)<=len(opciones):
                        raise ValueError
                    p['correcta'] = opciones[int(item.respuesta)-1]['id']
                except (ValueError, IndexError):
                    raise ValidationError('Hay una pregunta sin respuesta correcta. Avisá al equipo formador.')
            else:
                p['secuencia'] = [o['id'] for o in opciones]
            random.SystemRandom().shuffle(opciones)
            p['opciones'] = opciones
        elif prueba.tipo == 'memoria':
            p['opciones'] = relaciones
            p['correcta'] = str(item.pk)
        datos['preguntas'].append(p)
    return datos


def corregir(estructura, post):
    tipo = estructura['tipo']
    respuestas, puntos, total = {}, 0, 0
    if tipo == 'rompecabezas':
        orden = post.get('piezas', '').split(',')
        if len(orden) != 9 or set(orden) != set(estructura['solucion']):
            raise ValidationError('Completá el rompecabezas antes de entregarlo.')
        return {'piezas': orden}, round(100 * sum(a == b for a, b in zip(orden, estructura['solucion'])) / 9)
    for p in estructura['preguntas']:
        key = 'q_' + p['id']
        total += 1
        if tipo == 'ordenar':
            valor = post.getlist(key)
            if len(valor) != len(p['secuencia']) or set(valor) != set(p['secuencia']):
                raise ValidationError('En cada actividad usá todos los pasos una sola vez.')
            puntos += sum(a == b for a, b in zip(valor, p['secuencia'])) / len(valor)
        else:
            valor = post.get(key, '').strip()
            if not valor or len(valor) > 6000:
                raise ValidationError('Respondé todas las actividades antes de entregar (hasta 6000 caracteres por respuesta).')
            if tipo in {'trivia', 'camino', 'memoria'}:
                if valor not in {o['id'] for o in p['opciones']}:
                    raise ValidationError('Seleccioná una de las opciones de la actividad.')
                puntos += (normalizar(next(o['texto'] for o in p['opciones'] if o['id']==valor))==normalizar(p['respuesta'])) if tipo=='memoria' else valor == p['correcta']
            elif tipo == 'palabra':
                puntos += normalizar(valor) == normalizar(p['respuesta'])
        respuestas[p['id']] = valor
    return respuestas, None if tipo == 'ruleta' else round(100 * puntos / total)


def escena_actual(intento):
    datos = intento.estructura
    nodo = datos['inicio']
    for decision in intento.respuestas.get('ruta', []):
        opcion = next(o for o in datos['grafo'][nodo]['opciones'] if o['id'] == decision)
        nodo = opcion['destino']
    return nodo, datos['grafo'][nodo]
