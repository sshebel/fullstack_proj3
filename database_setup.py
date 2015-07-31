from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
 
Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    picture = Column(String(100), nullable=True)


 
class MenuItem(Base):
    __tablename__ = 'menu_item'


    name =Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    description = Column(String(250))
    price = Column(String(8))
    course = Column(String(250))
    restaurant_id = Column(Integer,ForeignKey('restaurant.id'))
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)


    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'description'         : self.description,
           'id'         : self.id,
           'price'         : self.price,
           'course'         : self.course,
       }

class Restaurant(Base):
    __tablename__ = 'restaurant'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    menu_item = relationship(MenuItem,single_parent=True,cascade="all,delete-orphan",backref="restaurant")
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
       }

engine = create_engine('sqlite:///restaurantmenuwithusers.db')
 

Base.metadata.create_all(engine)
