# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: bilibili/dagw/component/avatar/v1/avatar.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from util.api_common.bilibili_activity.protos.bilibili.dagw.component.avatar.common import common_pb2 as bilibili_dot_dagw_dot_component_dot_avatar_dot_common_dot_common__pb2
from util.api_common.bilibili_activity.protos.bilibili.dagw.component.avatar.v1 import plugin_pb2 as bilibili_dot_dagw_dot_component_dot_avatar_dot_v1_dot_plugin__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n.bilibili/dagw/component/avatar/v1/avatar.proto\x12!bilibili.dagw.component.avatar.v1\x1a\x32\x62ilibili/dagw/component/avatar/common/common.proto\x1a.bilibili/dagw/component/avatar/v1/plugin.proto\"\xe9\x01\n\nAvatarItem\x12G\n\x0e\x63ontainer_size\x18\x01 \x01(\x0b\x32/.bilibili.dagw.component.avatar.common.SizeSpec\x12=\n\x06layers\x18\x02 \x03(\x0b\x32-.bilibili.dagw.component.avatar.v1.LayerGroup\x12\x46\n\x0f\x66\x61llback_layers\x18\x03 \x01(\x0b\x32-.bilibili.dagw.component.avatar.v1.LayerGroup\x12\x0b\n\x03mid\x18\x04 \x01(\x03\"\x8a\x02\n\x12\x42\x61sicLayerResource\x12\x10\n\x08res_type\x18\x01 \x01(\x05\x12@\n\tres_image\x18\x02 \x01(\x0b\x32+.bilibili.dagw.component.avatar.v1.ResImageH\x00\x12H\n\rres_animation\x18\x03 \x01(\x0b\x32/.bilibili.dagw.component.avatar.v1.ResAnimationH\x00\x12K\n\x0fres_native_draw\x18\x04 \x01(\x0b\x32\x30.bilibili.dagw.component.avatar.v1.ResNativeDrawH\x00\x42\t\n\x07payload\"\x9d\x01\n\rGeneralConfig\x12X\n\rweb_css_style\x18\x01 \x03(\x0b\x32\x41.bilibili.dagw.component.avatar.v1.GeneralConfig.WebCssStyleEntry\x1a\x32\n\x10WebCssStyleEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"\x88\x02\n\x05Layer\x12\x10\n\x08layer_id\x18\x01 \x01(\t\x12\x0f\n\x07visible\x18\x02 \x01(\x08\x12M\n\x0cgeneral_spec\x18\x03 \x01(\x0b\x32\x37.bilibili.dagw.component.avatar.common.LayerGeneralSpec\x12\x44\n\x0clayer_config\x18\x04 \x01(\x0b\x32..bilibili.dagw.component.avatar.v1.LayerConfig\x12G\n\x08resource\x18\x05 \x01(\x0b\x32\x35.bilibili.dagw.component.avatar.v1.BasicLayerResource\"\xad\x02\n\x0bLayerConfig\x12\x46\n\x04tags\x18\x01 \x03(\x0b\x32\x38.bilibili.dagw.component.avatar.v1.LayerConfig.TagsEntry\x12\x13\n\x0bis_critical\x18\x02 \x01(\x08\x12\x18\n\x10\x61llow_over_paint\x18\x03 \x01(\x08\x12G\n\nlayer_mask\x18\x04 \x01(\x0b\x32\x33.bilibili.dagw.component.avatar.common.MaskProperty\x1a^\n\tTagsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12@\n\x05value\x18\x02 \x01(\x0b\x32\x31.bilibili.dagw.component.avatar.v1.LayerTagConfig:\x02\x38\x01\"\xbc\x01\n\nLayerGroup\x12\x10\n\x08group_id\x18\x01 \x01(\t\x12\x38\n\x06layers\x18\x02 \x03(\x0b\x32(.bilibili.dagw.component.avatar.v1.Layer\x12G\n\ngroup_mask\x18\x03 \x01(\x0b\x32\x33.bilibili.dagw.component.avatar.common.MaskProperty\x12\x19\n\x11is_critical_group\x18\x04 \x01(\x08\"\x8a\x03\n\x0eLayerTagConfig\x12\x13\n\x0b\x63onfig_type\x18\x01 \x01(\x05\x12J\n\x0egeneral_config\x18\x02 \x01(\x0b\x32\x30.bilibili.dagw.component.avatar.v1.GeneralConfigH\x00\x12K\n\x0bgyro_config\x18\x03 \x01(\x0b\x32\x34.bilibili.dagw.component.avatar.v1.plugin.GyroConfigH\x00\x12h\n\x1a\x63omment_doubleClick_config\x18\x04 \x01(\x0b\x32\x42.bilibili.dagw.component.avatar.v1.plugin.CommentDoubleClickConfigH\x00\x12V\n\x11live_anime_config\x18\x05 \x01(\x0b\x32\x39.bilibili.dagw.component.avatar.v1.plugin.LiveAnimeConfigH\x00\x42\x08\n\x06\x63onfig\"W\n\x0cResAnimation\x12G\n\x08webp_src\x18\x01 \x01(\x0b\x32\x35.bilibili.dagw.component.avatar.common.ResourceSource\"T\n\x08ResImage\x12H\n\timage_src\x18\x01 \x01(\x0b\x32\x35.bilibili.dagw.component.avatar.common.ResourceSource\"X\n\rResNativeDraw\x12G\n\x08\x64raw_src\x18\x01 \x01(\x0b\x32\x35.bilibili.dagw.component.avatar.common.ResourceSourceb\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'bilibili.dagw.component.avatar.v1.avatar_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _GENERALCONFIG_WEBCSSSTYLEENTRY._options = None
  _GENERALCONFIG_WEBCSSSTYLEENTRY._serialized_options = b'8\001'
  _LAYERCONFIG_TAGSENTRY._options = None
  _LAYERCONFIG_TAGSENTRY._serialized_options = b'8\001'
  _AVATARITEM._serialized_start=186
  _AVATARITEM._serialized_end=419
  _BASICLAYERRESOURCE._serialized_start=422
  _BASICLAYERRESOURCE._serialized_end=688
  _GENERALCONFIG._serialized_start=691
  _GENERALCONFIG._serialized_end=848
  _GENERALCONFIG_WEBCSSSTYLEENTRY._serialized_start=798
  _GENERALCONFIG_WEBCSSSTYLEENTRY._serialized_end=848
  _LAYER._serialized_start=851
  _LAYER._serialized_end=1115
  _LAYERCONFIG._serialized_start=1118
  _LAYERCONFIG._serialized_end=1419
  _LAYERCONFIG_TAGSENTRY._serialized_start=1325
  _LAYERCONFIG_TAGSENTRY._serialized_end=1419
  _LAYERGROUP._serialized_start=1422
  _LAYERGROUP._serialized_end=1610
  _LAYERTAGCONFIG._serialized_start=1613
  _LAYERTAGCONFIG._serialized_end=2007
  _RESANIMATION._serialized_start=2009
  _RESANIMATION._serialized_end=2096
  _RESIMAGE._serialized_start=2098
  _RESIMAGE._serialized_end=2182
  _RESNATIVEDRAW._serialized_start=2184
  _RESNATIVEDRAW._serialized_end=2272
# @@protoc_insertion_point(module_scope)