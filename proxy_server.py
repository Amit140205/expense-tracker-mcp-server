from fastmcp import FastMCP

# client => proxy => server
# claude desktop does not provide connector support to remote mcp server in free tier

mcp = FastMCP.as_proxy(
    "https://combative-cyan-wildebeest.fastmcp.app/mcp",
    name = "Amit Proxy Server"
)

if __name__ == "__main__":
    mcp.run()