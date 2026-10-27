# Glance Configuration with Shared YAML Library

This directory contains the Glance dashboard configuration using a shared YAML library system that leverages YAML anchors to minimize `$include` directives and promote code reuse.

## File Structure

```
config/
├── README.md              # This documentation file
├── glance.yml            # Main configuration file
├── shared-library.yml    # Shared YAML anchors library
├── home.yml             # Home page configuration
└── homelab.yml          # Homelab page configuration
```

## Shared Library System

### Overview

The shared library system uses YAML anchors (`&anchor-name`) and references (`*anchor-name`) to define reusable configuration snippets. This approach:

- **Reduces duplication**: Common configurations are defined once and reused
- **Minimizes `$include` directives**: Only one include for the shared library
- **Improves maintainability**: Changes to shared components propagate automatically
- **Enhances consistency**: Ensures uniform behavior across pages

### How It Works

1. **Define anchors** in `shared-library.yml` using the `&anchor-name` syntax
2. **Include the library** once in `glance.yml` using `$include: shared-library.yml`
3. **Reference anchors** in page files using the `*anchor-name` syntax

### Current Shared Components

#### `shared-search` (&shared-search)

A comprehensive search widget configuration with:
- DuckDuckGo as the default search engine
- Autofocus enabled for immediate typing
- Multiple search "bangs" for quick access to:
  - YouTube (`!yt`)
  - GitHub (`!gh`)
  - Reddit (`!r`)
  - Stack Overflow (`!so`)
  - Wikipedia (`!w`)

**Usage Example:**
```yaml
head-widgets: *shared-search
```

## Adding New Shared Components

To add new shared components to the library:

1. **Define the anchor** in `shared-library.yml`:
```yaml
# Example: Shared Reddit widget properties
shared-reddit-props: &shared-reddit-props
  type: reddit
  show-thumbnails: true
  collapse-after: 6
```

2. **Use the anchor** in your page configurations:
```yaml
- subreddit: technology
  <<: *shared-reddit-props
```

3. **Document the new component** in this README

## YAML Anchor Syntax Reference

### Basic Anchor Definition and Reference
```yaml
# Define an anchor
my-config: &my-anchor
  key: value
  another-key: another-value

# Reference the anchor
some-section: *my-anchor
```

### Merge Keys (Advanced)
```yaml
# Define base properties
base-props: &base
  type: widget
  cache: 5m

# Merge and extend
specific-widget:
  <<: *base          # Merge base properties
  title: "My Widget" # Add specific properties
  limit: 10
```

### Multiple Merges
```yaml
widget:
  <<: [*base-props, *style-props, *behavior-props]
  title: "Combined Widget"
```

## Best Practices

1. **Use descriptive anchor names**: `shared-search` instead of `search1`
2. **Group related anchors**: Keep similar configurations together
3. **Document new anchors**: Update this README when adding new shared components
4. **Test configurations**: Verify that anchor references work correctly
5. **Keep anchors focused**: Each anchor should represent a cohesive set of properties

## Troubleshooting

### Common Issues

1. **Anchor not found**: Ensure the shared library is included before using anchors
2. **Circular references**: Avoid anchors that reference themselves
3. **Merge conflicts**: When using `<<:`, later properties override earlier ones

### Debugging

Use Glance's configuration print command to see the resolved configuration:
```bash
glance --config /path/to/glance.yml config:print | less -N
```

## Migration from `$include` Directives

To migrate existing `$include` directives to the shared library system:

1. **Identify common patterns** in your included files
2. **Extract shared components** to `shared-library.yml` as anchors
3. **Replace `$include` with anchor references** in page files
4. **Test the configuration** to ensure it works correctly

## Future Enhancements

The shared library can be extended with additional components such as:

- Common widget styling properties
- Standard RSS feed configurations
- Reusable bookmark groups
- Common authentication settings
- Standard caching configurations

---

For more information about YAML anchors, see: https://support.atlassian.com/bitbucket-cloud/docs/yaml-anchors/
For Glance configuration documentation, see: https://github.com/glanceapp/glance/blob/main/docs/configuration.md