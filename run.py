from database import Base, engine; 
import models; Base.metadata.drop_all(engine); 
Base.metadata.create_all(engine)