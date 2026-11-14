import os

# torch and faiss-cpu each ship an OpenMP runtime on Windows. Without this flag the
# process can abort with "OMP: Error #15 ... libiomp5md.dll already initialized".
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")