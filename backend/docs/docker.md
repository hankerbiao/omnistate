### 启动mongo db

docker run -d     --name my-mongo-2     --hostname my-mongo     -p 27019:27017     mongo:7.0     --replSet rs0     --bind_ip_all
</br> 
docker exec -it my-mongo-2 mongosh --eval 'rs.initiate({_id:"rs0",members:[{_id:0,host:"10.17.154.252:27019"}]})'
</br> 
docker exec -it my-mongo-2 mongosh --eval 'rs.status()'