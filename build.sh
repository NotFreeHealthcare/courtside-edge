#!/bin/sh
# Wrap app.html (the artifact source) into a standalone index.html
cd "$(dirname "$0")"
{ printf '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#0A101C"><style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%%}[hidden]{display:none!important}</style></head><body>\n'; grep -v 'window.__CE_SNAP=' app.html; printf '\n</body></html>\n'; } > index.html
