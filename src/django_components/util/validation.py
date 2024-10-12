import sys
import typing
from typing import Any, Mapping, Tuple, get_type_hints

# Get all types that users may use from the `typing` module.
#
# These are the types that we do NOT try to resolve when it's a typed generic,
# e.g. `Union[int, str]`.
# If we get a typed generic that's NOT part of this set, we assume it's a user-made
# generic, e.g. `Component[Args, Kwargs]`. In such case we assert that a given value
# is an instance of the base class, e.g. `Component`.
_typing_exports = frozenset(
    [
        value
        for value in typing.__dict__.values()
        if isinstance(
            value,
            (
                typing._SpecialForm,
                # Used in 3.8 and 3.9
                getattr(typing, "_GenericAlias", ()),
                # Used in 3.11+ (possibly 3.10?)
                getattr(typing, "_SpecialGenericAlias", ()),
            ),
        )
    ]
)


def _prepare_type_for_validation(the_type: Any) -> Any:
    # If we got a typed generic (AKA "subscripted" generic), e.g.
    # `Component[CompArgs, CompKwargs, ...]`
    # then we cannot use that generic in `isintance()`, because we get this error:
    # `TypeError("Subscripted generics cannot be used with class and instance checks")`
    #
    # Instead, we resolve the generic to its original class, e.g. `Component`,
    # which can then be used in instance assertion.
    if hasattr(the_type, "__origin__"):
        is_custom_typing = the_type.__origin__ not in _typing_exports
        if is_custom_typing:
            return the_type.__origin__
        else:
            return the_type
    else:
        return the_type


# NOTE: tuple_type is a _GenericAlias - See https://stackoverflow.com/questions/74412803
def validate_typed_tuple(
    value: Tuple[Any, ...],
    tuple_type: Any,
    prefix: str,
    kind: str,
) -> None:
    # `Any` type is the signal that we should skip validation
    if tuple_type == Any:
        return

    # We do two kinds of validation with the given Tuple type:
    # 1. We check whether there are any extra / missing positional args
    # 2. We look at the members of the Tuple (which are types themselves),
    #    and check if our concrete list / tuple has correct types under correct indices.
    expected_pos_args = len(tuple_type.__args__)
    actual_pos_args = len(value)
    if expected_pos_args > actual_pos_args:
        # Generate errors like below (listed for searchability)
        # `Component 'name' expected 3 positional arguments, got 2`
        raise TypeError(f"{prefix} expected {expected_pos_args} {kind}s, got {actual_pos_args}")

    for index, arg_type in enumerate(tuple_type.__args__):
        arg = value[index]
        arg_type = _prepare_type_for_validation(arg_type)
        if sys.version_info >= (3, 11) and not isinstance(arg, arg_type):
            # Generate errors like below (listed for searchability)
            # `Component 'name' expected positional argument at index 0 to be <class 'int'>, got 123.5 of type <class 'float'>`  # noqa: E501
            raise TypeError(
                f"{prefix} expected {kind} at index {index} to be {arg_type}, got {arg} of type {type(arg)}"
            )


# NOTE:
# - `dict_type` can be a `TypedDict` or `Any` as the types themselves
# - `value` is expected to be TypedDict, the base `TypedDict` type cannot be used
#   in function signature (only its subclasses can), so we specify the type as Mapping.
#   See https://stackoverflow.com/questions/74412803
def validate_typed_dict(value: Mapping[str, Any], dict_type: Any, prefix: str, kind: str) -> None:
    # `Any` type is the signal that we should skip validation
    if dict_type == Any:
        return

    # See https://stackoverflow.com/a/76527675
    # And https://stackoverflow.com/a/71231688
    required_kwargs = dict_type.__required_keys__
    unseen_keys = set(value.keys())

    # For each entry in the TypedDict, we do two kinds of validation:
    # 1. We check whether there are any extra / missing keys
    # 2. We look at the values of TypedDict entries (which are types themselves),
    #    and check if our concrete dict has correct types under correct keys.
    for key, kwarg_type in get_type_hints(dict_type).items():
        if key not in value:
            if key in required_kwargs:
                # Generate errors like below (listed for searchability)
                # `Component 'name' is missing a required keyword argument 'key'`
                # `Component 'name' is missing a required slot argument 'key'`
                # `Component 'name' is missing a required data argument 'key'`
                raise TypeError(f"{prefix} is missing a required {kind} '{key}'")
        else:
            unseen_keys.remove(key)
            kwarg = value[key]
            kwarg_type = _prepare_type_for_validation(kwarg_type)

            # NOTE: `isinstance()` cannot be used with the version of TypedDict prior to 3.11.
            # So we do type validation for TypedDicts only in 3.11 and later.
            if sys.version_info >= (3, 11) and not isinstance(kwarg, kwarg_type):
                # Generate errors like below (listed for searchability)
                # `Component 'name' expected keyword argument 'key' to be <class 'int'>, got 123.4 of type <class 'float'>`  # noqa: E501
                # `Component 'name' expected slot 'key' to be <class 'int'>, got 123.4 of type <class 'float'>`
                # `Component 'name' expected data 'key' to be <class 'int'>, got 123.4 of type <class 'float'>`
                raise TypeError(
                    f"{prefix} expected {kind} '{key}' to be {kwarg_type}, got {kwarg} of type {type(kwarg)}"
                )

    if unseen_keys:
        formatted_keys = ", ".join([f"'{key}'" for key in unseen_keys])
        # Generate errors like below (listed for searchability)
        # `Component 'name' got unexpected keyword argument keys 'invalid_key'`
        # `Component 'name' got unexpected slot keys 'invalid_key'`
        # `Component 'name' got unexpected data keys 'invalid_key'`
        raise TypeError(f"{prefix} got unexpected {kind} keys {formatted_keys}")
