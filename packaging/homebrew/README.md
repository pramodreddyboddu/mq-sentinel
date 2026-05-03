# Homebrew distribution

To make `brew install pramodreddyboddu/tap/mq-sentinel` work, you create a
**tap repository** (a small standalone GitHub repo that Homebrew watches).

## One-time tap setup

```bash
gh repo create pramodreddyboddu/homebrew-tap \
  --public \
  --description "Homebrew tap for MQ-Sentinel and related tools" \
  --add-readme

git clone https://github.com/pramodreddyboddu/homebrew-tap.git
cd homebrew-tap
mkdir -p Formula
cp ../mq-sentinel/packaging/homebrew/mq-sentinel.rb Formula/
git add Formula/mq-sentinel.rb
git commit -m "Add mq-sentinel formula"
git push
```

## Updating the formula on each release

After tagging `v0.1.0` in the main repo:

```bash
# Get the tarball SHA256
TARBALL_SHA=$(curl -sL https://github.com/pramodreddyboddu/mq-sentinel/archive/refs/tags/v0.1.0.tar.gz \
  | shasum -a 256 | awk '{print $1}')

# In the tap repo:
sed -i "s|REPLACE_WITH_TAG_TARBALL_SHA256|${TARBALL_SHA}|" Formula/mq-sentinel.rb
sed -i "s|tags/v[0-9]*\.[0-9]*\.[0-9]*|tags/v0.1.0|" Formula/mq-sentinel.rb
git commit -am "mq-sentinel 0.1.0"
git push
```

## CI: auto-bump the formula

Add `.github/workflows/release.yml` step in the **tap** repo:

```yaml
on:
  repository_dispatch:
    types: [mq-sentinel-released]

jobs:
  bump:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          VERSION="${{ github.event.client_payload.version }}"
          SHA="${{ github.event.client_payload.tarball_sha256 }}"
          sed -i "s|REPLACE_WITH_TAG_TARBALL_SHA256|${SHA}|" Formula/mq-sentinel.rb
          sed -i "s|tags/v[0-9]*\.[0-9]*\.[0-9]*|tags/v${VERSION}|" Formula/mq-sentinel.rb
      - uses: peter-evans/create-pull-request@v6
        with:
          title: "mq-sentinel ${{ github.event.client_payload.version }}"
          commit-message: "mq-sentinel ${{ github.event.client_payload.version }}"
          branch: "bump/mq-sentinel-${{ github.event.client_payload.version }}"
```

Then in the main repo's `release.yml`, after publishing the release:

```yaml
- name: Trigger tap formula bump
  run: |
    gh api repos/pramodreddyboddu/homebrew-tap/dispatches \
      -X POST \
      -f event_type=mq-sentinel-released \
      -f "client_payload[version]=${GITHUB_REF_NAME#v}" \
      -f "client_payload[tarball_sha256]=${TARBALL_SHA}"
```

## After tap is published

User experience:

```bash
brew tap pramodreddyboddu/tap
brew install mq-sentinel

# Or in one line:
brew install pramodreddyboddu/tap/mq-sentinel
```

Mac developers — including hiring managers at IBM — will install MQ-Sentinel
in 30 seconds.
