# pulls dashboard
Dashboard for systematic view of pull requests of a selected repository

Avaliable at https://pulls-dashboard-demo.herokuapp.com/

## To run locally:

Install all libraries from requirements.txt

You have to have variable GITHUB_TOKEN set in the environment, otherwise you may exceed allowed limit for not authenticated requests ("https://developer.github.com/v3/#rate-limiting")

Also set "MONGODB_URI" and "DB_NAME" and run your MongoDB, use the db in which you want to keep data about all repositories, all pull requests, and all people, labels and tests mentioned in these pulls. 

``` console
export FLASK_APP=pulls_dashboard.py

flask run
```

Then open localhost

You can you refresh repo's data by using the button from the interface (on dashboard page), or open '/task' to update all "saved" repos, but also you can create a cron job to execute ./run_task.sh once in some time

## Heroku

Use same config variables, and free add-ons Heroku Scheduler and mLab MongoDB



