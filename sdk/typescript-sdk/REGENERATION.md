# SDK Regeneration Guide

This document explains how to safely regenerate the TypeScript SDK without losing custom code.

## Protected Files

The following files are protected from regeneration via `.openapi-generator-ignore`:

1. **`src/client.ts`** - Custom wrapper with heartbeat management and SSE support
2. **`README.md`** - Custom documentation with usage examples  
3. **`package.json`** - Modified with custom dependencies and metadata

## Regeneration Command

To regenerate the SDK after updating the OpenAPI spec:

```bash
cd /Users/sohansarabu/Documents/plato-client/sdk

docker run --rm \
  -v "${PWD}/openapi:/spec" \
  -v "${PWD}/typescript-sdk:/output" \
  openapitools/openapi-generator-cli:latest generate \
  -i /spec/plato.yaml \
  -g typescript-fetch \
  -o /output \
  --additional-properties=npmName=@plato-ai/sdk,supportsES6=true,typescriptThreePlus=true
```

## What Gets Updated

When you regenerate:

✅ **Generated files will be updated:**
- `src/apis/*.ts` - All API client classes
- `src/models/*.ts` - All model/type definitions
- `src/runtime.ts` - Runtime utilities
- `tsconfig.json`, `tsconfig.esm.json` - TypeScript configs

❌ **Protected files will NOT be overwritten:**
- `src/client.ts` - Your custom wrapper
- `README.md` - Your documentation
- `package.json` - Your package configuration

## After Regeneration

1. **Check for breaking changes:**
   ```bash
   npm run build
   ```

2. **Update client.ts if needed:**
   - If API method names changed, update `src/client.ts`
   - If new APIs were added, optionally expose them in `PlatoClient`

3. **Re-install dependencies:**
   ```bash
   npm install
   ```

4. **Test the build:**
   ```bash
   npm run build
   ```

## File Structure

```
typescript-sdk/
├── .openapi-generator-ignore  ← Protection rules
├── src/
│   ├── client.ts             ← PROTECTED - Custom wrapper
│   ├── index.ts              ← PROTECTED by package.json - Exports wrapper
│   ├── apis/                 ← Generated (updated on regeneration)
│   ├── models/               ← Generated (updated on regeneration)
│   └── runtime.ts            ← Generated (updated on regeneration)
├── package.json              ← PROTECTED - Custom config
└── README.md                 ← PROTECTED - Custom docs
```

## Important Notes

1. **Always backup before regenerating** (though protected files should be safe)
2. **Check git diff** after regeneration to see what changed
3. **The wrapper extends generated APIs**, so changes to API method signatures may require updating `client.ts`
4. **Dependencies in package.json** won't be lost (it's protected)

## Common Issues

### API method names changed
- **Solution:** Search for the old method name in generated `src/apis/` files and update `client.ts`

### New required parameters added
- **Solution:** Update method calls in `client.ts` to include new parameters

### Response types changed
- **Solution:** Update type annotations in `client.ts` if using explicit types

### Build fails after regeneration
- **Solution:** Run `npm install` to ensure all dependencies are up-to-date

