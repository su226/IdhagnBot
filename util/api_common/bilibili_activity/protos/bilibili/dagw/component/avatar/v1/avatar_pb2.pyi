"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import util.api_common.bilibili_activity.protos.bilibili.dagw.component.avatar.common.common_pb2
import util.api_common.bilibili_activity.protos.bilibili.dagw.component.avatar.v1.plugin_pb2
import builtins
import collections.abc
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.message
import sys

if sys.version_info >= (3, 8):
    import typing as typing_extensions
else:
    import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing_extensions.final
class AvatarItem(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    CONTAINER_SIZE_FIELD_NUMBER: builtins.int
    LAYERS_FIELD_NUMBER: builtins.int
    FALLBACK_LAYERS_FIELD_NUMBER: builtins.int
    MID_FIELD_NUMBER: builtins.int
    @property
    def container_size(self) -> bilibili.dagw.component.avatar.common.common_pb2.SizeSpec:
        """"""
    @property
    def layers(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[global___LayerGroup]:
        """"""
    @property
    def fallback_layers(self) -> global___LayerGroup:
        """"""
    mid: builtins.int
    """"""
    def __init__(
        self,
        *,
        container_size: bilibili.dagw.component.avatar.common.common_pb2.SizeSpec | None = ...,
        layers: collections.abc.Iterable[global___LayerGroup] | None = ...,
        fallback_layers: global___LayerGroup | None = ...,
        mid: builtins.int = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["container_size", b"container_size", "fallback_layers", b"fallback_layers"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["container_size", b"container_size", "fallback_layers", b"fallback_layers", "layers", b"layers", "mid", b"mid"]) -> None: ...

global___AvatarItem = AvatarItem

@typing_extensions.final
class BasicLayerResource(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    RES_TYPE_FIELD_NUMBER: builtins.int
    RES_IMAGE_FIELD_NUMBER: builtins.int
    RES_ANIMATION_FIELD_NUMBER: builtins.int
    RES_NATIVE_DRAW_FIELD_NUMBER: builtins.int
    res_type: builtins.int
    """"""
    @property
    def res_image(self) -> global___ResImage:
        """"""
    @property
    def res_animation(self) -> global___ResAnimation:
        """"""
    @property
    def res_native_draw(self) -> global___ResNativeDraw:
        """/"""
    def __init__(
        self,
        *,
        res_type: builtins.int = ...,
        res_image: global___ResImage | None = ...,
        res_animation: global___ResAnimation | None = ...,
        res_native_draw: global___ResNativeDraw | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["payload", b"payload", "res_animation", b"res_animation", "res_image", b"res_image", "res_native_draw", b"res_native_draw"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["payload", b"payload", "res_animation", b"res_animation", "res_image", b"res_image", "res_native_draw", b"res_native_draw", "res_type", b"res_type"]) -> None: ...
    def WhichOneof(self, oneof_group: typing_extensions.Literal["payload", b"payload"]) -> typing_extensions.Literal["res_image", "res_animation", "res_native_draw"] | None: ...

global___BasicLayerResource = BasicLayerResource

@typing_extensions.final
class GeneralConfig(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    @typing_extensions.final
    class WebCssStyleEntry(google.protobuf.message.Message):
        DESCRIPTOR: google.protobuf.descriptor.Descriptor

        KEY_FIELD_NUMBER: builtins.int
        VALUE_FIELD_NUMBER: builtins.int
        key: builtins.str
        value: builtins.str
        def __init__(
            self,
            *,
            key: builtins.str = ...,
            value: builtins.str = ...,
        ) -> None: ...
        def ClearField(self, field_name: typing_extensions.Literal["key", b"key", "value", b"value"]) -> None: ...

    WEB_CSS_STYLE_FIELD_NUMBER: builtins.int
    @property
    def web_css_style(self) -> google.protobuf.internal.containers.ScalarMap[builtins.str, builtins.str]:
        """"""
    def __init__(
        self,
        *,
        web_css_style: collections.abc.Mapping[builtins.str, builtins.str] | None = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["web_css_style", b"web_css_style"]) -> None: ...

global___GeneralConfig = GeneralConfig

@typing_extensions.final
class Layer(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    LAYER_ID_FIELD_NUMBER: builtins.int
    VISIBLE_FIELD_NUMBER: builtins.int
    GENERAL_SPEC_FIELD_NUMBER: builtins.int
    LAYER_CONFIG_FIELD_NUMBER: builtins.int
    RESOURCE_FIELD_NUMBER: builtins.int
    layer_id: builtins.str
    """"""
    visible: builtins.bool
    """"""
    @property
    def general_spec(self) -> bilibili.dagw.component.avatar.common.common_pb2.LayerGeneralSpec:
        """"""
    @property
    def layer_config(self) -> global___LayerConfig:
        """"""
    @property
    def resource(self) -> global___BasicLayerResource:
        """"""
    def __init__(
        self,
        *,
        layer_id: builtins.str = ...,
        visible: builtins.bool = ...,
        general_spec: bilibili.dagw.component.avatar.common.common_pb2.LayerGeneralSpec | None = ...,
        layer_config: global___LayerConfig | None = ...,
        resource: global___BasicLayerResource | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["general_spec", b"general_spec", "layer_config", b"layer_config", "resource", b"resource"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["general_spec", b"general_spec", "layer_config", b"layer_config", "layer_id", b"layer_id", "resource", b"resource", "visible", b"visible"]) -> None: ...

global___Layer = Layer

@typing_extensions.final
class LayerConfig(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    @typing_extensions.final
    class TagsEntry(google.protobuf.message.Message):
        DESCRIPTOR: google.protobuf.descriptor.Descriptor

        KEY_FIELD_NUMBER: builtins.int
        VALUE_FIELD_NUMBER: builtins.int
        key: builtins.str
        @property
        def value(self) -> global___LayerTagConfig: ...
        def __init__(
            self,
            *,
            key: builtins.str = ...,
            value: global___LayerTagConfig | None = ...,
        ) -> None: ...
        def HasField(self, field_name: typing_extensions.Literal["value", b"value"]) -> builtins.bool: ...
        def ClearField(self, field_name: typing_extensions.Literal["key", b"key", "value", b"value"]) -> None: ...

    TAGS_FIELD_NUMBER: builtins.int
    IS_CRITICAL_FIELD_NUMBER: builtins.int
    ALLOW_OVER_PAINT_FIELD_NUMBER: builtins.int
    LAYER_MASK_FIELD_NUMBER: builtins.int
    @property
    def tags(self) -> google.protobuf.internal.containers.MessageMap[builtins.str, global___LayerTagConfig]:
        """"""
    is_critical: builtins.bool
    """"""
    allow_over_paint: builtins.bool
    """"""
    @property
    def layer_mask(self) -> bilibili.dagw.component.avatar.common.common_pb2.MaskProperty:
        """"""
    def __init__(
        self,
        *,
        tags: collections.abc.Mapping[builtins.str, global___LayerTagConfig] | None = ...,
        is_critical: builtins.bool = ...,
        allow_over_paint: builtins.bool = ...,
        layer_mask: bilibili.dagw.component.avatar.common.common_pb2.MaskProperty | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["layer_mask", b"layer_mask"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["allow_over_paint", b"allow_over_paint", "is_critical", b"is_critical", "layer_mask", b"layer_mask", "tags", b"tags"]) -> None: ...

global___LayerConfig = LayerConfig

@typing_extensions.final
class LayerGroup(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    GROUP_ID_FIELD_NUMBER: builtins.int
    LAYERS_FIELD_NUMBER: builtins.int
    GROUP_MASK_FIELD_NUMBER: builtins.int
    IS_CRITICAL_GROUP_FIELD_NUMBER: builtins.int
    group_id: builtins.str
    """"""
    @property
    def layers(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[global___Layer]:
        """"""
    @property
    def group_mask(self) -> bilibili.dagw.component.avatar.common.common_pb2.MaskProperty:
        """"""
    is_critical_group: builtins.bool
    """"""
    def __init__(
        self,
        *,
        group_id: builtins.str = ...,
        layers: collections.abc.Iterable[global___Layer] | None = ...,
        group_mask: bilibili.dagw.component.avatar.common.common_pb2.MaskProperty | None = ...,
        is_critical_group: builtins.bool = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["group_mask", b"group_mask"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["group_id", b"group_id", "group_mask", b"group_mask", "is_critical_group", b"is_critical_group", "layers", b"layers"]) -> None: ...

global___LayerGroup = LayerGroup

@typing_extensions.final
class LayerTagConfig(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    CONFIG_TYPE_FIELD_NUMBER: builtins.int
    GENERAL_CONFIG_FIELD_NUMBER: builtins.int
    GYRO_CONFIG_FIELD_NUMBER: builtins.int
    COMMENT_DOUBLECLICK_CONFIG_FIELD_NUMBER: builtins.int
    LIVE_ANIME_CONFIG_FIELD_NUMBER: builtins.int
    config_type: builtins.int
    """"""
    @property
    def general_config(self) -> global___GeneralConfig:
        """"""
    @property
    def gyro_config(self) -> bilibili.dagw.component.avatar.v1.plugin_pb2.GyroConfig:
        """"""
    @property
    def comment_doubleClick_config(self) -> bilibili.dagw.component.avatar.v1.plugin_pb2.CommentDoubleClickConfig:
        """"""
    @property
    def live_anime_config(self) -> bilibili.dagw.component.avatar.v1.plugin_pb2.LiveAnimeConfig:
        """"""
    def __init__(
        self,
        *,
        config_type: builtins.int = ...,
        general_config: global___GeneralConfig | None = ...,
        gyro_config: bilibili.dagw.component.avatar.v1.plugin_pb2.GyroConfig | None = ...,
        comment_doubleClick_config: bilibili.dagw.component.avatar.v1.plugin_pb2.CommentDoubleClickConfig | None = ...,
        live_anime_config: bilibili.dagw.component.avatar.v1.plugin_pb2.LiveAnimeConfig | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["comment_doubleClick_config", b"comment_doubleClick_config", "config", b"config", "general_config", b"general_config", "gyro_config", b"gyro_config", "live_anime_config", b"live_anime_config"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["comment_doubleClick_config", b"comment_doubleClick_config", "config", b"config", "config_type", b"config_type", "general_config", b"general_config", "gyro_config", b"gyro_config", "live_anime_config", b"live_anime_config"]) -> None: ...
    def WhichOneof(self, oneof_group: typing_extensions.Literal["config", b"config"]) -> typing_extensions.Literal["general_config", "gyro_config", "comment_doubleClick_config", "live_anime_config"] | None: ...

global___LayerTagConfig = LayerTagConfig

@typing_extensions.final
class ResAnimation(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    WEBP_SRC_FIELD_NUMBER: builtins.int
    @property
    def webp_src(self) -> bilibili.dagw.component.avatar.common.common_pb2.ResourceSource:
        """"""
    def __init__(
        self,
        *,
        webp_src: bilibili.dagw.component.avatar.common.common_pb2.ResourceSource | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["webp_src", b"webp_src"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["webp_src", b"webp_src"]) -> None: ...

global___ResAnimation = ResAnimation

@typing_extensions.final
class ResImage(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    IMAGE_SRC_FIELD_NUMBER: builtins.int
    @property
    def image_src(self) -> bilibili.dagw.component.avatar.common.common_pb2.ResourceSource:
        """"""
    def __init__(
        self,
        *,
        image_src: bilibili.dagw.component.avatar.common.common_pb2.ResourceSource | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["image_src", b"image_src"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["image_src", b"image_src"]) -> None: ...

global___ResImage = ResImage

@typing_extensions.final
class ResNativeDraw(google.protobuf.message.Message):
    """"""

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    DRAW_SRC_FIELD_NUMBER: builtins.int
    @property
    def draw_src(self) -> bilibili.dagw.component.avatar.common.common_pb2.ResourceSource:
        """"""
    def __init__(
        self,
        *,
        draw_src: bilibili.dagw.component.avatar.common.common_pb2.ResourceSource | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["draw_src", b"draw_src"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["draw_src", b"draw_src"]) -> None: ...

global___ResNativeDraw = ResNativeDraw