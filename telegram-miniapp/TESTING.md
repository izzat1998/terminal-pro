# MTT Telegram Mini App - Testing Guide

This document describes the test setup for the Telegram Mini App.

## Test Framework

- **Vitest 4.0.17** - Fast Vite-native test runner
- **React Testing Library** - For React component testing
- **Happy DOM** - Lightweight DOM implementation
- **@vitest/coverage-v8** - Code coverage reporting

## Running Tests

```bash
# Run all tests once
npm run test

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui

# Run tests with coverage report
npm run test:coverage
```

## Test Structure

```
telegram-miniapp/
├── src/
│   ├── __tests__/          # Global test setup
│   │   └── setup.ts        # Test environment configuration
│   ├── __mocks__/          # Global mocks
│   │   └── telegram-sdk.ts # Telegram Mini Apps SDK mock
│   ├── contexts/
│   │   └── __tests__/
│   │       └── CameraContext.test.tsx
│   └── pages/
│       └── __tests__/
│           └── CameraPage.test.tsx
├── vitest.config.ts        # Vitest configuration
└── TESTING.md              # This file
```

## What's Tested

### CameraContext (15 tests)

**Provider setup:**
- ✓ Context provider initialization
- ✓ Hook usage outside provider throws error

**Camera stream management:**
- ✓ Request camera access and return stream
- ✓ Call getUserMedia with correct constraints
- ✓ Reuse existing active stream instead of creating new one
- ✓ Create new stream if previous one was stopped

**Camera stream cleanup:**
- ✓ Stop all tracks when stopCamera is called
- ✓ Handle stopCamera when no stream exists
- ✓ Cleanup stream on unmount
- ✓ Set isCameraActive to false when track ends

**Error handling:**
- ✓ Handle getUserMedia errors gracefully
- ✓ Return null and log error on camera access failure

**Context state management:**
- ✓ Provide consistent stream reference
- ✓ Update state when stopping camera

### CameraPage / API Integration (21 tests)

**API Error Handling (9 tests):**
- ✓ Handle choices fetch failure
- ✓ Handle destinations fetch failure
- ✓ Handle plate recognition API error
- ✓ Handle vehicle entry submission error
- ✓ Handle network errors
- ✓ Handle successful choices fetch
- ✓ Handle successful destinations fetch
- ✓ Handle successful plate recognition
- ✓ Handle failed plate recognition

**Vehicle Options Builder (5 tests):**
- ✓ Build correct option tree for light vehicles
- ✓ Build correct option tree for cargo vehicles
- ✓ Include container options for platform vehicles
- ✓ Exclude container options for non-platform vehicles
- ✓ Handle empty destination list

**Image Utilities (4 tests):**
- ✓ Convert base64 to blob with correct MIME type
- ✓ Handle PNG base64 strings
- ✓ Create FormData with photo
- ✓ Use default parameters for FormData

**Canvas and Video mocks (3 tests):**
- ✓ Mock canvas.toDataURL with JPEG quality
- ✓ Mock canvas.getContext
- ✓ Mock video.play

## Coverage Report

```
-------------------|---------|----------|---------|---------|
File               | % Stmts | % Branch | % Funcs | % Lines |
-------------------|---------|----------|---------|---------|
All files          |   84.37 |    63.63 |   96.29 |   83.87 |
 contexts          |     100 |      100 |     100 |     100 |
  CameraContext    |     100 |      100 |     100 |     100 |
 helpers           |   44.44 |       20 |   66.66 |   44.44 |
  imageUtils       |   44.44 |       20 |   66.66 |   44.44 |
 utils             |     100 |      100 |     100 |     100 |
  vehicleOptions   |     100 |      100 |     100 |     100 |
-------------------|---------|----------|---------|---------|
```

## Test Environment Setup

### Global Mocks

**MediaDevices API:**
- MockMediaStream with proper track management
- MockMediaStreamTrack with lifecycle simulation
- getUserMedia mocked to return functional streams

**HTMLCanvasElement:**
- getContext('2d') returns mock context with drawImage
- toDataURL returns mock base64 data

**HTMLVideoElement:**
- play() returns resolved promise
- pause() mocked

**Fetch API:**
- Global fetch is mocked via `vi.fn()`
- Tests configure responses per scenario

### Telegram SDK Mock

Located in `src/__mocks__/telegram-sdk.ts`:

- Complete WebApp API mock
- Mock hooks: useLaunchParams, useInitData, useMiniApp, etc.
- Mock user data for testing
- resetTelegramMock() function for cleanup

## Writing New Tests

### Test Pattern for Components

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';

describe('ComponentName', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should do something', async () => {
    // Arrange
    const mockData = { /* ... */ };

    // Act
    const { result } = render(<Component />);

    // Assert
    await waitFor(() => {
      expect(result).toBeDefined();
    });
  });
});
```

### Test Pattern for Context

```typescript
import { renderHook, act } from '@testing-library/react';

it('should manage state correctly', async () => {
  const wrapper = ({ children }) => (
    <Provider>{children}</Provider>
  );

  const { result } = renderHook(() => useContext(), { wrapper });

  await act(async () => {
    await result.current.someAction();
  });

  expect(result.current.someState).toBe(expectedValue);
});
```

## Best Practices

1. **Isolate tests**: Each test should be independent
2. **Clear mocks**: Always clear mocks in beforeEach
3. **Use act()**: Wrap state updates in act()
4. **Wait for async**: Use waitFor() for async operations
5. **Test behavior**: Test what users see, not implementation details
6. **Mock external deps**: Mock API calls, camera, Telegram SDK
7. **Descriptive names**: Use clear test descriptions

## Common Issues

### Issue: MediaStream undefined

**Solution:** Ensure getUserMedia mock returns a proper stream:
```typescript
vi.spyOn(navigator.mediaDevices, 'getUserMedia')
  .mockResolvedValue(new MockMediaStream() as unknown as MediaStream);
```

### Issue: Act warnings

**Solution:** Wrap async state updates in act():
```typescript
await act(async () => {
  await result.current.someAsyncAction();
});
```

### Issue: Test isolation failures

**Solution:** Clean up in afterEach:
```typescript
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
```

## Future Enhancements

- [ ] Add E2E tests with Playwright
- [ ] Add visual regression tests
- [ ] Increase imageUtils coverage
- [ ] Add performance testing
- [ ] Add accessibility testing (a11y)

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
