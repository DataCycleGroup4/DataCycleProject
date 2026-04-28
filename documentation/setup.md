# This solution requires:
- A windows VM
- A Knime EduHub / BusinessHub account
- A GCP account

Once you've set up accounts and all the infrastructure you need, you can find the specific info in each respective subsection of this page.

## Windows VM

Your VM is going to be performing the majority of the hard work. 
So, you're going to need to set up the environment for it.

First install python on your Windows VM. If you want to use a Linux VM instead, check if python is already installed (it usually is). You can download python from here https://www.python.org/downloads/

You're going to edit some values in the project. Notepad will be enough, but you can download Notepad++ from here https://notepad-plus-plus.org/downloads/

Extract the .zip of the solution on the VM.

Now, navigate to the root directory of the solution, and create a file called `.env`. This is a hidden file where you will set constant values called *environment variables* read by the different scripts in the solution. These are user-specific, so are not saved to the distributed version of the solution. Here's a list of the variables:

NOTE: UPDATE THESE AFTER ALEX HAS SORTED ALL THIS OUT

- `HMAC_ACCESS_KEY`
- `HMAC_SECRET_KEY`
- `KNIME_ID`
- `KNIME_PASSWORD`

If you haven't set up the GCP and Knime environment fully, you won't have all these values yet. Once you've finished setting them up, just come back to the `.env` file and update them.


You're nearly done!

All you need to do now is open Windows Task Scheduler, and create a basic task to scheduled to run `manager.py` daily. Finished!

## GCP

Here's a list of all cloud resources you're going to need to set up.
1. A cloud storage bucket
2. A BigQuery dataset
3. A Sub/pub
4. A Cloud Workflow
5. A service account


## Knime

This solution was developed in an academic environment, where we had access to Knime's EduHub. Private customers can use the BusinessHub.

Download Knime on your client from here https://www.knime.com/downloads

Log in to your account and create a space, then import the file `Group4EnergyPredictions.knwf` + your GCP auth json file into the space, then deploy it.

Next, go to your deployed workflow in Knime's Hub (whichever one you're using) and create a version. Select service. This has now deployed your workflow to the Hub which can be reached via an API.

