import sqlite3


class DBHelper:
    def __init__(self, dbname='mydatabase.db'):
        self.dbname = dbname
        self.connect = sqlite3.connect(dbname)
        self.args = []

    def setup(self):
        sql = """CREATE TABLE IF NOT EXISTS information
        (user_id INT, destination VARCHAR, hotels_amount INT, photos_amount INT)"""
        self.connect.execute(sql)
        self.connect.commit()

    def add_item(self):
        sql = """INSERT INTO information(args) VALUES (?,?,?,?)"""
        self.connect.execute(sql, self.args)
        self.connect.commit()

    # def delete_item(self, item_text):
    #     stmt = "DELETE FROM items WHERE description = (?)"
    #     args = (item_text, )
    #     self.conn.execute(stmt, args)
    #     self.conn.commit()
    #
    # def get_items(self):
    #     stmt = "SELECT description FROM items"
    #     return [x[0] for x in self.conn.execute(stmt)]
