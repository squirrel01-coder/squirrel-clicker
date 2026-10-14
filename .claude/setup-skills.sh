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

# plugin <плагин@маркетплейс> <github-repo-маркетплейса>
PLUGINS=()
plugin() { PLUGINS+=("$1|$2"); }

# ---------- СПИСОК СКИЛЛОВ ----------
skill humanizer https://github.com/blader/humanizer.git

# ---------- СПИСОК ПЛАГИНОВ ----------
plugin document-skills@anthropic-agent-skills anthropics/skills
plugin ui-ux-pro-max@ui-ux-pro-max-skill nextlevelbuilder/ui-ux-pro-max-skill
plugin marketing-skills@marketingskills coreyhaines31/marketingskills
plugin last30days@last30days-skill mvanhorn/last30days-skill

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
