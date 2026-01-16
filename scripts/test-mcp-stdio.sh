echo "🧪 Test MCP Server Catalog..."

cat > /tmp/mcp-test.jsonl <<EOF
{"jsonrpc":"2.0","id":1,"method":"initialize"}
{"jsonrpc":"2.0","id":2,"method":"listTools"}
{"jsonrpc":"2.0","id":3,"method":"callTool","params":{"name":"catalog.searchLowStock","arguments":{"threshold":15}}}
EOF

docker compose exec -T mcp-server-catalog sh -c "cat /tmp/mcp-test.jsonl | python server.py"

echo "✅ Test completato!"
