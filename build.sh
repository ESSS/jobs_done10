if [ $# -eq 0 ]
  then
    echo "Version not given"
    exit 1
fi

IMAGE_NAME=docker.esss.co/jobs_done

docker build . --tag $IMAGE_NAME:$1 --build-arg SETUPTOOLS_SCM_PRETEND_VERSION=$1
docker tag $IMAGE_NAME:$1 $IMAGE_NAME:latest
docker push $IMAGE_NAME:$1
docker push $IMAGE_NAME:latest
