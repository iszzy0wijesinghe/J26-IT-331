"""Launch with: python -m apps.c3_workbench"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("apps.c3_workbench.api:app", host="127.0.0.1", port=8033, reload=False)
