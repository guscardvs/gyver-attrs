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
