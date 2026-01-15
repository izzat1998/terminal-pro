# MTT Code Quality Rules

These rules MUST be followed when writing or modifying code in the MTT project.

## Rule 1: Service Layer Pattern (Backend)

**MUST:** All business logic goes in service classes (`apps/*/services/`), never in views or serializers.

**Views should only:**
- Validate request data (via serializers)
- Call service methods
- Format and return responses

**Example - WRONG:**
```python
# In views.py - DON'T DO THIS
def exit_vehicle(self, request):
    entry = VehicleEntry.objects.get(license_plate=plate)
    entry.status = "EXITED"  # ❌ Business logic in view
    entry.exit_time = timezone.now()
    entry.save()
```

**Example - CORRECT:**
```python
# In views.py - DO THIS
def exit_vehicle(self, request):
    entry_service = VehicleEntryService()
    entry = entry_service.register_exit(license_plate=plate)  # ✅ Service handles logic
    return Response({"success": True, "data": serializer.data})
```

---

## Rule 2: Custom Exceptions

**MUST:** Use custom exceptions from `apps/core/exceptions.py` for business logic errors.

**Available exceptions:**
- `BusinessLogicError` - General business rule violation
- `ContainerNotFoundError` - Container doesn't exist
- `DuplicateEntryError` - Duplicate record attempted
- `InvalidContainerStateError` - Invalid state transition

**Example - WRONG:**
```python
raise Exception("Vehicle not found")  # ❌ Generic exception
```

**Example - CORRECT:**
```python
from apps.core.exceptions import BusinessLogicError
raise BusinessLogicError("Транспорт не найден", code="VEHICLE_NOT_FOUND")  # ✅
```

---

## Rule 3: Response Format

**MUST:** All API responses follow the standard format.

**Success:**
```python
return Response({
    "success": True,
    "data": serializer.data,
    "message": "Optional message"  # Russian
})
```

**Error:**
```python
return Response({
    "success": False,
    "error": {
        "code": "ERROR_CODE",
        "message": "Сообщение об ошибке",  # Russian
        "details": {...}  # Optional
    }
}, status=status.HTTP_400_BAD_REQUEST)
```

---

## Rule 4: Language

**MUST:** Use appropriate language for each context.

| Context | Language |
|---------|----------|
| Variable names | English |
| Function names | English |
| Code comments | English |
| User-facing messages | Russian |
| Error messages (for users) | Russian |
| Log messages | English |
| API documentation | English |

**Example:**
```python
# English comment explaining logic
def register_exit(self, license_plate: str) -> VehicleEntry:
    if not entry:
        raise BusinessLogicError(
            "Транспорт с таким номером не найден на территории"  # Russian for user
        )
    self.logger.info(f"Registered exit for {license_plate}")  # English for logs
```

---

## Rule 5: Error Handling

**MUST:** Handle errors at appropriate layers.

**Services:** Raise custom exceptions with Russian messages
**Views:** Let exception handler catch and format (or handle explicitly for custom responses)
**Frontend:** Display error messages to users

**Never:** Catch and silently ignore errors, use bare `except:`, or expose stack traces to users.

---

## Rule 6: TypeScript Strict Mode (Frontend)

**MUST:** Follow TypeScript strict mode rules.

**Forbidden:**
- `any` type
- Implicit any
- Unchecked null access

**Required:**
- Explicit type annotations on functions
- Props typed with `defineProps<T>()`
- Emits typed with `defineEmits<T>()`

---

## Rule 7: Vue Composition API (Frontend)

**MUST:** Use `<script setup lang="ts">` syntax exclusively.

**Forbidden:**
- Options API (`export default { data(), methods: {} }`)
- Missing `lang="ts"` attribute
- Importing Ant Design components (they're global)

---

## Rule 8: No Over-Engineering

**MUST:** Keep solutions minimal and focused.

**Forbidden:**
- Adding features not requested
- Creating abstractions for single-use code
- Adding error handling for impossible scenarios
- Adding comments to obvious code
- Creating utility functions for one-off operations

**Required:**
- Only change what was asked
- Trust internal code and framework guarantees
- Three similar lines is better than premature abstraction

---

## Enforcement

These rules are NON-NEGOTIABLE. When writing code for MTT:

1. ✅ Check if change follows service layer pattern
2. ✅ Check if using custom exceptions
3. ✅ Check if response format is correct
4. ✅ Check if language is appropriate
5. ✅ Check if not over-engineering

If any rule would be violated, either:
- Refactor to comply with the rule
- Ask the user if they want an exception (with explanation of why)
