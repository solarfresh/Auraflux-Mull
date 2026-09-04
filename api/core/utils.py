from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from django.conf import settings
from rest_framework.exceptions import ValidationError


def create_serialized_data(data: Dict[str, Any], serializer_class, **save_kwargs)-> Dict[str, Any]:
    serializer = serializer_class(data=data)
    if serializer.is_valid():
        serializer.save(**save_kwargs)
        return serializer.data
    else:
        raise ValidationError(serializer.errors)

def delete_instance_by_query(query: Dict, model_class):
    instance = model_class.objects.get(**query)
    instance.delete()

def get_serialized_data(
    query: Dict,
    model_class,
    serializer_class,
    many: bool = True,
    prefetch_related: Optional[List[Union[str, object]]] = None,
    select_related: Optional[List[str]] = None
):
    queryset = model_class.objects.filter(**query)

    if prefetch_related:
        queryset = queryset.prefetch_related(*prefetch_related)

    if select_related:
        queryset = queryset.select_related(*select_related)

    if many:
        instances = queryset.all()
    else:
        instances = queryset.get()

    serializer = serializer_class(instances, many=many)
    return serializer.data

def get_serialized_data_by_id(id: UUID, model_class, serializer_class):
    instance = model_class.objects.get(id=id)
    serializer = serializer_class(instance)
    return serializer.data

def instance_to_data(instance, serializer_class, many=True):
    serializer = serializer_class(instance, many=many)
    return serializer.data

def update_serialized_data_by_id(id: UUID, data: Dict[str, Any], model_class, serializer_class):
    instance = model_class.objects.get(id=id)
    serializer = serializer_class(
        instance=instance,
        data=data,
        partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return serializer.data
    else:
        raise ValidationError(serializer.errors)

def update_serialized_data_by_query(query: Dict, data: Dict[str, Any], model_class, serializer_class):
    instance = model_class.objects.get(**query)
    serializer = serializer_class(
        instance=instance,
        data=data,
        partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return serializer.data
    else:
        raise ValidationError(serializer.errors)
