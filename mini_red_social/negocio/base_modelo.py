class BaseModelo:
    """
    Clase base para los modelos (Usuario, Publicacion).
    Define una interfaz común para operaciones CRUD.
    Esto cumple con los Criterios 2.1.2.4 (Herencia) y 2.1.2.6 (Polimorfismo).
    """

    def guardar(self, conn):
        """Método polimórfico para guardar (crear) un nuevo registro."""
        raise NotImplementedError("El método 'guardar' debe ser implementado por la subclase.")

    def actualizar(self, conn):
        """Método polimórfico para actualizar un registro existente."""
        raise NotImplementedError("El método 'actualizar' debe ser implementado por la subclase.")

    def eliminar(self, conn):
        """Método polimórfico para eliminar un registro."""
        raise NotImplementedError("El método 'eliminar' debe ser implementado por la subclase.")

    @staticmethod
    def listar_todos(conn):
        """Método polimórfico estático para listar todos los registros."""
        raise NotImplementedError("El método 'listar_todos' debe ser implementado por la subclase.")