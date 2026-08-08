#!/usr/bin/env bash
set -euo pipefail

freecad_mcp_root="${FREECAD_MCP_ROOT:-${XDG_DATA_HOME:-${HOME}/.local/share}/freecad-mcp}"
freecad_gui_bin="${FREECAD_MCP_FREECAD_BIN:-${HOME}/.local/opt/freecad/FreeCAD_1.1.1-Linux-x86_64-py311.AppImage}"
freecad_mcp_python="${freecad_mcp_root}/.venv/bin/python"
freecad_mcp_server="${freecad_mcp_root}/freecad_mcp_server.py"

if [[ ! -x "${freecad_mcp_python}" ]]; then
  echo "FreeCAD MCP Python is missing or not executable: ${freecad_mcp_python}" >&2
  echo "Set FREECAD_MCP_ROOT to the pinned freecad-mcp installation." >&2
  exit 1
fi

if [[ ! -f "${freecad_mcp_server}" ]]; then
  echo "FreeCAD MCP server is missing: ${freecad_mcp_server}" >&2
  exit 1
fi

if [[ ! -x "${freecad_gui_bin}" ]]; then
  echo "FreeCAD executable is missing or not executable: ${freecad_gui_bin}" >&2
  echo "Set FREECAD_MCP_FREECAD_BIN to the approved FreeCAD executable." >&2
  exit 1
fi

export FREECAD_MCP_FREECAD_BIN="${freecad_gui_bin}"
exec "${freecad_mcp_python}" "${freecad_mcp_server}"
