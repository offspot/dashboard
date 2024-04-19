# dashboard

Caddy-based file server serving static file with home-page generated on startup

## Configuration

Configuration is done via a YAML file describing the contents that should be exposed.

| Variable               | Usage                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------ |
| `metadata`             | A dict containing hompage-level metadata                                                   |
| **`metadata.name`**    | Hotspot name                                                                               |
| **`metadata.fqdn`**    | Domain name of the hotspot. Used to build links                                            |
| `packages`             | A list of `package` dicts describing each content package                                  |
| **`package.title`**    | Main name of content                                                                       |
| `package.kind`         | Kind of package, to adjust display and filters                                             |
| `package.description`  | Short description of the content                                                           |
| `package.languages`    | List of ISO-639-3 language code the content relates to                                     |
| `package.tags`         | List of Tag strings helping users guess what to expect from content                        |
| `package.icon`         | Base64 encoded 48x48px PNG image                                                           |
| **`package.url`**      | URL to access the content on the hotspot. Accepts some variables                           |
| `package.download.url` | URL to download the content from (for hotspot users)                                       |
| `package.download.size`| Size of the download file to download. Informative only                                    |

Main goal of this tool being linking to content, `package.url` accepts different helpers which are rewritten automatically:

- `{fqdn}` is replaced by the content of `metadata.fqdn`.
- `{service-fqdn}` is replaced by the service's subdomain. Ex: `{kiwix-fqdn}` may become `kiwix.myname.hotspot`.
- URLs not starting with a scheme (`urllib.parse.urlparse`) will be prefixed with `//`.
- `//` is the only scheme-less prefix allowed.
- Use `http://` or `https://` to enforce protocol.
- You can use external links (at your own risk of it not working)
- Other protocols alike.

### Sample

```yaml
---
metadata:
  name: My Hotspot
  fqdn: renaud.Hotspot
packages:
  kind: zim
  title: ArchWiki
  description: Arch Linux documentation
  languages:
  - eng
  tags:
  - archlinux
  url: //{kiwix-fqdn}/archlinux_en_all_maxi_2022-04
  download:
    url: //{zimdl-fqdn}/archlinux_en_all_maxi_2022-04.zim
    size: 32M
```

In addition, the `DEBUG` environ can be set to enable Caddy debug output.