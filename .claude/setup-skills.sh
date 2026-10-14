#!/bin/bash
# Ставит все скиллы и плагины пользователя в ~/.claude — для КАЖДОЙ сессии, в любом репозитории.
# Setup script облачного окружения скачивает этот файл при старте каждой сессии:
#   curl -fsSL https://raw.githubusercontent.com/squirrel01-coder/squirrel-clicker/HEAD/.claude/setup-skills.sh | bash
# Чтобы добавить скилл: допишите строку skill/plugin ниже и запушьте в основную ветку.

mkdir -p ~/.claude/skills

# skill <имя> <git-url> [подпапка-внутри-репо]
skill() {
  local name=$1 url=$2 sub=${3:-} tmp
  rm -rf ~/.claude/skills/"$name"
  if [ -z "$sub" ]; then
    git clone -q --depth 1 "$url" ~/.claude/skills/"$name" || echo "skill $name: clone failed"
  else
    tmp=$(mktemp -d) && git clone -q --depth 1 "$url" "$tmp" && cp -r "$tmp/$sub" ~/.claude/skills/"$name"
    rm -rf "$tmp"
  fi
}

# skillpack <git-url> <папка-внутри-репо> — ставит все скиллы из этой папки (каждая подпапка с SKILL.md)
skillpack() {
  local url=$1 sub=$2 tmp d
  tmp=$(mktemp -d)
  if git clone -q --depth 1 "$url" "$tmp"; then
    for d in "$tmp/$sub"/*/; do
      [ -f "$d/SKILL.md" ] || continue
      rm -rf ~/.claude/skills/"$(basename "$d")"
      cp -rL "$d" ~/.claude/skills/"$(basename "$d")"
    done
  else
    echo "skillpack $url: clone failed"
  fi
  rm -rf "$tmp"
}

# plugin <плагин@маркетплейс> <github-repo-маркетплейса>
PLUGINS=()
plugin() { PLUGINS+=("$1|$2"); }

# ---------- СПИСОК СКИЛЛОВ ----------
skill humanizer https://github.com/blader/humanizer.git
skillpack https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git .claude/skills
skillpack https://github.com/coreyhaines31/marketingskills.git skills
skillpack https://github.com/mvanhorn/last30days-skill.git skills

# ---------- СПИСОК ПЛАГИНОВ ----------
plugin document-skills@anthropic-agent-skills anthropics/skills

# Прописываем плагины в ~/.claude/settings.json (существующие настройки сохраняются)
printf '%s\n' "${PLUGINS[@]}" | python3 -c '
import json, os, sys
p = os.path.expanduser("~/.claude/settings.json")
s = json.load(open(p)) if os.path.exists(p) else {}
for line in filter(None, sys.stdin.read().splitlines()):
    pid, repo = line.split("|")
    mk = pid.split("@")[1]
    s.setdefault("extraKnownMarketplaces", {})[mk] = {"source": {"source": "github", "repo": repo}}
    s.setdefault("enabledPlugins", {})[pid] = True
json.dump(s, open(p, "w"), indent=2)
'
echo "skills: $(ls ~/.claude/skills | tr '\n' ' ')"
exit 0
