## 0.7.1 (2023-10-01)

### Fix

- added support for __dataclass_transform__ format

## 0.7.0 (2023-09-12)

### Feat

- Updated code to support ForwardRef

## 0.6.0 (2023-09-10)

## 0.5.4 (2023-08-14)

## 0.5.3 (2023-08-14)

### Feat

- **schemas**: extended schema support for different cases and creates specialist classes for schemas

### Fix

- changed arguments in shortcuts to match defaults on define
- **build**: fixed wrong version for gyver-attrs-converter
- **helpers**: added schema_class helper to make pydantic default as false and fixed mutable to pass frozen=False

## 0.3.0 (2023-03-09)

### Feat

- added helpers to integrate with pydantic, dataclasses and other helpers
- created core features for gyver-attrs
- **hash**: created hashable objects
- added converters serializers and a MethodBuilder
- added __parse_dict__ function to speedup serialization
- **descriptors**: removed optin format of descriptor support, support is now for every descriptor
- **methods**: added repr and eq

### Fix

- added direct support to dataclasses.field
- **gserialize**: now gserialize works correctly with sequence fields
- fixed _get_hash function
- fixed bug where serialization did not handle typealias
- fixed ellipsis import
- fixed importing conflicts
